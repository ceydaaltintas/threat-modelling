"""Runs left behind when the backend stops mid-analysis.

The pipeline lives in an asyncio task inside this process, so a restart (or
a crash) kills it while the database still says ``running``. Nothing would
ever advance such a run again: the screen sits on the same step forever with
no error to show. On startup we look for those rows and say plainly what
happened, so the step can be retried.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import AnalysisRun, RunStep

logger = logging.getLogger(__name__)

# Both mean "someone in this process is looking after it", and after a
# restart nobody is: waiting_user is an in-memory event just like running.
INTERRUPTED = ("running", "waiting_user")

RUN_MESSAGE = (
    "Analiz, sunucu yeniden başlatıldığı için yarıda kaldı. Tamamlanan "
    "adımların çıktıları ve verilen uzman kararları duruyor; kaldığı adımı "
    "yeniden çalıştırabilirsiniz."
)
STEP_MESSAGE = "Sunucu yeniden başlatıldı; bu adım yarıda kaldı."
WAITING_MESSAGE = (
    "Sunucu yeniden başlatıldı; bu adım beklemeye devam edemedi. "
    "Yeniden çalıştırın."
)


async def sweep_interrupted_runs() -> int:
    """Mark interrupted runs and their open steps as failed. Returns count."""
    now = datetime.now(timezone.utc)
    async with SessionLocal() as session:
        runs = (
            await session.execute(
                select(AnalysisRun).where(AnalysisRun.status.in_(INTERRUPTED))
            )
        ).scalars().all()

        for run in runs:
            run.status = "failed"
            run.finished_at = run.finished_at or now
            run.error_message = RUN_MESSAGE

            steps = (
                await session.execute(
                    select(RunStep)
                    .where(RunStep.run_id == run.id)
                    .where(RunStep.status.in_(INTERRUPTED))
                )
            ).scalars().all()
            for step in steps:
                waiting = step.status == "waiting_user"
                step.status = "failed"
                step.finished_at = step.finished_at or now
                step.message = WAITING_MESSAGE if waiting else STEP_MESSAGE

        if runs:
            await session.commit()
            logger.warning(
                "%s analiz yarıda kalmıştı; başarısız olarak işaretlendi.",
                len(runs),
            )
    return len(runs)
