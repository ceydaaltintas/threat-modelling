"""Analysis run endpoints, including the live progress stream (SSE)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.audit.service import record as audit_record
from app.core.config import get_settings
from app.core.db import get_session
from app.core.events import broker
from app.core.samples import sample_by_key
from app.models import AnalysisRun, Project, RunStep
from app.pipeline import PIPELINE_STEPS
from app.pipeline import mock_runner
from app.schemas.api import RunCreate, RunOut

router = APIRouter(prefix="/api/runs", tags=["runs"])

# Keep-alive interval for the event stream (seconds).
SSE_PING_INTERVAL = 15

# Phase 0 has no real identity provider; the role switcher sends this header.
DEMO_ACTOR_HEADER = "x-demo-actor"
DEMO_ROLE_HEADER = "x-demo-role"


def _actor(request: Request) -> tuple[str, str]:
    actor = request.headers.get(DEMO_ACTOR_HEADER) or "demo@ornekbanka.local"
    role = request.headers.get(DEMO_ROLE_HEADER) or "security_expert"
    return actor, role


async def _load_run(session: AsyncSession, run_id: str) -> AnalysisRun:
    run = (
        await session.execute(
            select(AnalysisRun)
            .options(selectinload(AnalysisRun.steps))
            .where(AnalysisRun.id == run_id)
        )
    ).scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı.")
    project = await session.get(Project, run.project_id)
    # Attached for serialisation only; not a mapped column.
    run.project_name = project.name if project else None
    return run


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: RunCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnalysisRun:
    """Create a run and start it.

    Phase 0: the steps are driven by ``pipeline.mock_runner`` with placeholder
    data. The run, its steps and the event stream are real.
    """
    settings = get_settings()
    actor, role = _actor(request)

    name = payload.project_name
    if payload.sample_key:
        scenario = sample_by_key(payload.sample_key)
        if scenario is None:
            raise HTTPException(status_code=400, detail="Bilinmeyen örnek senaryo.")
        name = name or scenario.title

    project = Project(
        name=name or "Adsız analiz",
        description=None,
        sample_key=payload.sample_key,
    )
    session.add(project)
    await session.flush()

    run = AnalysisRun(
        project_id=project.id,
        status="pending",
        llm_settings={
            "provider": settings.llm_provider,
            "model": settings.llm_model or None,
            "temperature": settings.llm_temperature,
        },
        demo_replay=settings.demo_replay,
        auto_continue=payload.auto_continue,
    )
    session.add(run)
    await session.flush()

    for step in PIPELINE_STEPS:
        session.add(
            RunStep(run_id=run.id, step_no=step.no, name=step.name, status="pending")
        )

    await audit_record(
        session,
        actor=actor,
        actor_role=role,
        action="run_created",
        object_type="analysis_run",
        object_id=run.id,
        run_id=run.id,
        new_value={
            "project": project.name,
            "sample_key": payload.sample_key,
            "auto_continue": payload.auto_continue,
            "build_phase": 0,
        },
    )
    await session.commit()

    await mock_runner.start(run.id)
    return await _load_run(session, run.id)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> AnalysisRun:
    return await _load_run(session, run_id)


@router.post("/{run_id}/resume", response_model=RunOut)
async def resume_run(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnalysisRun:
    """Release a run that is waiting for the user (model approval, review)."""
    run = await _load_run(session, run_id)
    actor, role = _actor(request)

    # Read the paused step before resuming: once the runner is released it
    # clears that state. The model-approval pause happens *after* step 2
    # completes, so the step row is already "done" and the runner is the only
    # place that knows which step is holding the run.
    waiting = mock_runner.paused_at(run_id) or next(
        (s.step_no for s in run.steps if s.status == "waiting_user"), None
    )

    if not mock_runner.request_resume(run_id):
        raise HTTPException(
            status_code=409,
            detail="Bu analiz şu anda kullanıcı onayı beklemiyor.",
        )
    await audit_record(
        session,
        actor=actor,
        actor_role=role,
        action="run_resumed",
        object_type="analysis_run",
        object_id=run_id,
        run_id=run_id,
        new_value={"resumed_at_step": waiting},
    )
    await session.commit()
    return await _load_run(session, run_id)


@router.post("/{run_id}/cancel", response_model=RunOut)
async def cancel_run(
    run_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnalysisRun:
    await _load_run(session, run_id)
    actor, role = _actor(request)
    await mock_runner.stop(run_id)
    await audit_record(
        session,
        actor=actor,
        actor_role=role,
        action="run_cancelled",
        object_type="analysis_run",
        object_id=run_id,
        run_id=run_id,
    )
    await session.commit()
    return await _load_run(session, run_id)


@router.get("/{run_id}/log")
async def run_log(run_id: str) -> list[dict[str, Any]]:
    """Events emitted so far - used when the page is opened after the fact."""
    return await broker.history(run_id)


@router.get("/{run_id}/events")
async def run_events(run_id: str, request: Request) -> EventSourceResponse:
    """Server-Sent Events stream of live progress.

    A late subscriber first receives the backlog so the stepper is correct
    immediately after a page reload.
    """
    queue, backlog = await broker.subscribe(run_id)

    async def event_source() -> AsyncGenerator[dict[str, Any], None]:
        try:
            for event in backlog:
                yield {"event": "progress", "data": _dump(event)}
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=SSE_PING_INTERVAL)
                except asyncio.TimeoutError:
                    yield {"event": "ping", "data": "{}"}
                    continue
                yield {"event": "progress", "data": _dump(event)}
        finally:
            await broker.unsubscribe(run_id, queue)

    return EventSourceResponse(event_source())


def _dump(event: dict[str, Any]) -> str:
    import json

    return json.dumps(event, ensure_ascii=False, default=str)
