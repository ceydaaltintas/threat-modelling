"""Analysis run endpoints, including the live progress stream (SSE)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from fastapi.responses import FileResponse

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sse_starlette.sse import EventSourceResponse

from app.audit.service import record as audit_record
from pathlib import Path

from app.core.config import get_settings
from app.core.db import get_session
from app.core.events import broker
from app.core.samples import sample_by_key
from app.core import storage
from app.reports import storage as report_storage
from app.models import AnalysisRun, Document, Project, RunStep, SystemModel
from app.pipeline import PIPELINE_STEPS, extract, progress, runner
from app.pipeline.steps import step_by_no
from app.schemas.system_model import SystemModel as SystemModelSchema
from app.schemas.api import (
    DocumentOut,
    RunCreate,
    RunOut,
    SystemModelOut,
    SystemModelUpdate,
)

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


async def _create_project_and_run(
    session: AsyncSession,
    *,
    name: str,
    sample_key: str | None,
    auto_continue: bool,
) -> tuple[Project, AnalysisRun]:
    settings = get_settings()
    project = Project(name=name, sample_key=sample_key)
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
        auto_continue=auto_continue,
    )
    session.add(run)
    await session.flush()

    for step in PIPELINE_STEPS:
        session.add(
            RunStep(run_id=run.id, step_no=step.no, name=step.name, status="pending")
        )
    return project, run


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: RunCreate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnalysisRun:
    """Create a run from one of the bundled sample scenarios and start it."""
    actor, role = _actor(request)

    if not payload.sample_key:
        raise HTTPException(
            status_code=400,
            detail="Örnek senaryo seçin veya dosya yükleyin (/api/runs/upload).",
        )
    scenario = sample_by_key(payload.sample_key)
    if scenario is None:
        raise HTTPException(status_code=400, detail="Bilinmeyen örnek senaryo.")
    if not scenario.available:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Örnek doküman bulunamadı: {scenario.filename}. "
                "samples/documents klasörünü kontrol edin."
            ),
        )

    project, run = await _create_project_and_run(
        session,
        name=payload.project_name or scenario.title,
        sample_key=payload.sample_key,
        auto_continue=payload.auto_continue,
    )

    # The sample goes through exactly the same path as an upload.
    document = Document(
        project_id=project.id,
        filename=scenario.filename,
        doc_type=extract.detect_doc_type(scenario.filename),
        mime_type="application/pdf",
        size_bytes=scenario.size_bytes,
    )
    session.add(document)
    await session.flush()
    document.storage_path = str(storage.copy_file(document.id, scenario.path))

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
            "documents": [scenario.filename],
        },
    )
    await session.commit()

    await runner.start(run.id)
    return await _load_run(session, run.id)


@router.post(
    "/upload", response_model=RunOut, status_code=status.HTTP_201_CREATED
)
async def create_run_from_upload(
    request: Request,
    files: list[UploadFile] = File(...),
    project_name: str | None = Form(default=None),
    auto_continue: bool = Form(default=False),
    session: AsyncSession = Depends(get_session),
) -> AnalysisRun:
    """Upload one or more architecture documents and start an analysis."""
    settings = get_settings()
    actor, role = _actor(request)

    if not files:
        raise HTTPException(status_code=400, detail="Hiç dosya gönderilmedi.")

    max_bytes = min(
        settings.max_upload_mb * 1024 * 1024, storage.ABSOLUTE_MAX_BYTES
    )

    # Read and validate everything before creating any row.
    prepared: list[tuple[UploadFile, bytes, str]] = []
    for upload in files:
        try:
            doc_type = extract.detect_doc_type(upload.filename or "")
        except extract.UnsupportedDocument as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        data = await upload.read()
        if len(data) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"'{upload.filename}' çok büyük "
                    f"({len(data) // (1024 * 1024)} MB). "
                    f"Sınır: {settings.max_upload_mb} MB."
                ),
            )
        if not data:
            raise HTTPException(
                status_code=400, detail=f"'{upload.filename}' boş görünüyor."
            )
        prepared.append((upload, data, doc_type))

    default_name = Path(prepared[0][0].filename or "Adsız analiz").stem
    project, run = await _create_project_and_run(
        session,
        name=project_name or default_name,
        sample_key=None,
        auto_continue=auto_continue,
    )

    filenames: list[str] = []
    for upload, data, doc_type in prepared:
        document = Document(
            project_id=project.id,
            filename=upload.filename or "dosya",
            doc_type=doc_type,
            mime_type=upload.content_type,
            size_bytes=len(data),
        )
        session.add(document)
        await session.flush()
        document.storage_path = str(
            storage.save_bytes(document.id, document.filename, data)
        )
        filenames.append(document.filename)

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
            "documents": filenames,
            "auto_continue": auto_continue,
        },
    )
    await session.commit()

    await runner.start(run.id)
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
    waiting = runner.paused_at(run_id) or next(
        (s.step_no for s in run.steps if s.status == "waiting_user"), None
    )

    if not runner.request_resume(run_id):
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
    await runner.stop(run_id)
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


@router.get("/{run_id}/documents", response_model=list[DocumentOut])
async def run_documents(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> list[Document]:
    """Extracted text and the page/section index, for the step 1 panel."""
    run = await _load_run(session, run_id)
    return (
        await session.execute(
            select(Document)
            .where(Document.project_id == run.project_id)
            .order_by(Document.created_at)
        )
    ).scalars().all()


@router.get("/{run_id}/system-model", response_model=SystemModelOut)
async def get_system_model(
    run_id: str, session: AsyncSession = Depends(get_session)
) -> SystemModel:
    """The latest version of the extracted (and possibly edited) model."""
    await _load_run(session, run_id)
    row = (
        await session.execute(
            select(SystemModel)
            .where(SystemModel.run_id == run_id)
            .order_by(SystemModel.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Bu analiz için henüz sistem modeli çıkarılmadı.",
        )
    return row


@router.put("/{run_id}/system-model", response_model=SystemModelOut)
async def update_system_model(
    run_id: str,
    payload: SystemModelUpdate,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> SystemModel:
    """Store an expert's edit as a new version.

    The incoming data is validated against the same schema the LLM output
    goes through, so a hand edit cannot put an invalid model into the
    pipeline. The previous version is kept; nothing is overwritten.
    """
    await _load_run(session, run_id)
    actor, role = _actor(request)
    if role == "manager":
        raise HTTPException(
            status_code=403,
            detail="Yönetici rolü salt okunurdur; modeli düzenleyemez.",
        )

    try:
        validated = SystemModelSchema.model_validate(payload.data)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Sistem modeli geçerli değil: {exc.errors()[0]['msg']}",
        ) from exc

    previous = (
        await session.execute(
            select(SystemModel)
            .where(SystemModel.run_id == run_id)
            .order_by(SystemModel.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    row = SystemModel(
        run_id=run_id,
        version=(previous.version + 1) if previous else 1,
        data=validated.model_dump(mode="json"),
        source="expert",
    )
    session.add(row)

    await audit_record(
        session,
        actor=actor,
        actor_role=role,
        action="system_model_edited",
        object_type="system_model",
        object_id=row.id,
        run_id=run_id,
        old_value={
            "version": previous.version if previous else None,
            "components": len((previous.data or {}).get("components", []))
            if previous
            else 0,
        },
        new_value={
            "version": row.version,
            "components": len(validated.components),
            "flows": len(validated.data_flows),
        },
        reason=payload.reason,
    )
    await session.commit()
    await session.refresh(row)
    return row


@router.post("/{run_id}/steps/{step_no}/retry", response_model=RunOut)
async def retry_step(
    run_id: str,
    step_no: int,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> AnalysisRun:
    """Re-run a single step and continue the pipeline from there."""
    await _load_run(session, run_id)
    actor, role = _actor(request)
    if role == "manager":
        raise HTTPException(
            status_code=403,
            detail="Yönetici rolü salt okunurdur; adım çalıştıramaz.",
        )
    try:
        step_by_no(step_no)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Böyle bir adım yok.") from exc

    # Steps after this one are stale; mark them pending again.
    rows = (
        await session.execute(
            select(RunStep).where(
                RunStep.run_id == run_id, RunStep.step_no >= step_no
            )
        )
    ).scalars().all()
    for row in rows:
        row.status = "pending"
        row.progress = 0.0
        row.message = None
        row.counters = None
        row.output = None
        row.started_at = None
        row.finished_at = None

    await audit_record(
        session,
        actor=actor,
        actor_role=role,
        action="step_retried",
        object_type="run_step",
        object_id=run_id,
        run_id=run_id,
        new_value={"step": step_no},
    )
    await session.commit()

    # Without this the rail keeps the old statuses until a reload: restarting
    # from step 1 left step 2 showing green while step 1 was running again.
    for row in rows:
        await progress.publish_step(run_id, step_by_no(row.step_no), "pending")

    await runner.retry_step(run_id, step_no)
    return await _load_run(session, run_id)


@router.get("/{run_id}/reports/{name}")
async def download_report(
    run_id: str, name: str, session: AsyncSession = Depends(get_session)
):
    """Serve a generated report file.

    Only the four known filenames are served, so a crafted name cannot reach
    anything else on disk.
    """
    await _load_run(session, run_id)
    path = report_storage.report_path(run_id, name)
    if path is None:
        raise HTTPException(
            status_code=404,
            detail="Rapor bulunamadı. 9. adımı çalıştırın.",
        )
    return FileResponse(
        path,
        media_type=report_storage.ALLOWED[name],
        filename=name,
    )
