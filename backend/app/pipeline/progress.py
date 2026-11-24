"""Step bookkeeping: persist status and publish it on the event stream.

Every step goes through here, so the database row and the SSE event can never
drift apart.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from app.core.db import SessionLocal
from app.core.events import broker
from app.models import AnalysisRun, RunStep
from app.pipeline.steps import StepDefinition


def now() -> datetime:
    return datetime.now(tz=timezone.utc)


async def save_step(
    run_id: str,
    step_no: int,
    *,
    status: str,
    progress: float | None = None,
    message: str | None = None,
    counters: dict[str, int] | None = None,
    output: dict | None = None,
    started: bool = False,
    finished: bool = False,
) -> None:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(RunStep).where(
                    RunStep.run_id == run_id, RunStep.step_no == step_no
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return
        row.status = status
        if progress is not None:
            row.progress = progress
        if message is not None:
            row.message = message
        if counters is not None:
            row.counters = counters
        if output is not None:
            row.output = output
        if started:
            row.started_at = now()
            row.finished_at = None
            # The panel reads this; keeping the previous run's output made
            # a re-running step show the old result and the old error.
            row.output = None
            row.counters = None
        if finished:
            row.finished_at = now()
        await session.commit()


async def save_run(run_id: str, **fields: Any) -> None:
    async with SessionLocal() as session:
        run = await session.get(AnalysisRun, run_id)
        if run is None:
            return
        for key, value in fields.items():
            setattr(run, key, value)
        await session.commit()


async def publish_step(
    run_id: str,
    step: StepDefinition,
    status: str,
    *,
    progress: float = 0.0,
    message: str | None = None,
    counters: dict[str, int] | None = None,
    llm: dict[str, Any] | None = None,
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    placeholder: bool = False,
) -> None:
    await broker.publish(
        run_id,
        {
            "type": "step",
            "step": step.no,
            "step_name": step.name,
            "status": status,
            "progress": round(progress, 2),
            "message": message,
            "counters": counters or {},
            "llm": llm or {},
            "started_at": started_at.isoformat() if started_at else None,
            "finished_at": finished_at.isoformat() if finished_at else None,
            "placeholder": placeholder,
        },
    )


async def publish_run(
    run_id: str, status: str, message: str, *, placeholder: bool = False
) -> None:
    await broker.publish(
        run_id,
        {
            "type": "run",
            "status": status,
            "message": message,
            "placeholder": placeholder,
        },
    )


async def publish_event(run_id: str, payload: dict[str, Any]) -> None:
    await broker.publish(run_id, payload)
