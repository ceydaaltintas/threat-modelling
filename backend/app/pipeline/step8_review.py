"""Step 8 - the expert's own work.

Nothing is computed here: the step reports where the review stands and the
run waits until the expert says they are done. Every decision they make
lands in the audit trail through the review endpoints.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select

from app.core.db import SessionLocal
from app.models import Threat
from app.pipeline.context import RunContext
from app.pipeline.steps import step_by_no

logger = logging.getLogger(__name__)

STEP = step_by_no(8)


async def review_counts(run_id: str) -> dict[str, int]:
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(Threat.review_status, func.count())
                .where(Threat.run_id == run_id)
                .group_by(Threat.review_status)
            )
        ).all()
    counts = {status: count for status, count in rows}
    total = sum(counts.values())
    pending = counts.get("pending", 0)
    return {
        "total": total,
        "pending": pending,
        "accepted": counts.get("accepted", 0),
        "rejected": counts.get("rejected", 0),
        "false_positive": counts.get("false_positive", 0),
        "edited": counts.get("edited", 0),
        "decided": total - pending,
    }


async def snapshot(ctx: RunContext) -> dict[str, int]:
    """Counts for the stepper while the run waits for the expert."""
    counts = await review_counts(ctx.run_id)
    ctx.step_output[STEP.no] = counts
    return counts
