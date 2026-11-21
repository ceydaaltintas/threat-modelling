"""Step 6 - compute the risk score for every threat.

Pure code. For each threat the rule context (or, for an LLM threat, the
STRIDE baseline) is combined with the context adjustments, clamped to 1..5
and turned into a score, a level and a breakdown the UI prints verbatim.

The LLM's own likelihood/impact suggestion stays untouched on the threat row
and is shown next to the computed value, never merged into it.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Threat
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.steps import step_by_no
from app.risk import Thresholds, score_threat

logger = logging.getLogger(__name__)

STEP = step_by_no(6)


def _rule_context(threat: Threat) -> dict | None:
    for note in threat.validation_notes or []:
        if note.get("code") == "rule_context":
            return note.get("data")
    return None


async def run(ctx: RunContext) -> dict[str, int]:
    thresholds = Thresholds(
        low=ctx.settings.risk_threshold_low,
        medium=ctx.settings.risk_threshold_medium,
        high=ctx.settings.risk_threshold_high,
    )

    async with SessionLocal() as session:
        threats = (
            await session.execute(
                select(Threat)
                .where(Threat.run_id == ctx.run_id)
                .order_by(Threat.created_at)
            )
        ).scalars().all()
        if not threats:
            raise StepFailed("Risk hesaplanacak tehdit yok (4. adımı çalıştırın).")

        by_level = {"Kritik": 0, "Yüksek": 0, "Orta": 0, "Düşük": 0}
        # How often the computed level differs from what the LLM proposed.
        ai_differs = 0
        heat: dict[str, int] = {}

        for index, threat in enumerate(threats, start=1):
            result = score_threat(
                stride=threat.stride,
                rule_context=_rule_context(threat),
                has_evidence=bool(threat.evidence),
                thresholds=thresholds,
            )
            threat.system_calc = result.as_dict()
            by_level[result.level] = by_level.get(result.level, 0) + 1
            heat_key = f"{result.likelihood}x{result.impact}"
            heat[heat_key] = heat.get(heat_key, 0) + 1

            proposed = threat.ai_proposed or {}
            if proposed.get("likelihood") and proposed.get("impact"):
                proposed_score = proposed["likelihood"] * proposed["impact"]
                if thresholds.level_for(proposed_score) != result.level:
                    ai_differs += 1

            if index % 10 == 0 or index == len(threats):
                await ctx.report(
                    STEP,
                    progress_value=index / len(threats),
                    message=f"Risk hesaplanıyor {index}/{len(threats)}",
                    counters={
                        "critical": by_level["Kritik"],
                        "high": by_level["Yüksek"],
                    },
                )

        await session.commit()

    ctx.step_output[STEP.no] = {
        "by_level": by_level,
        "heatmap": heat,
        "thresholds": {
            "low": thresholds.low,
            "medium": thresholds.medium,
            "high": thresholds.high,
        },
        "ai_level_differs": ai_differs,
        "total": len(threats),
    }

    return {
        "critical": by_level["Kritik"],
        "high": by_level["Yüksek"],
        "medium": by_level["Orta"],
        "low": by_level["Düşük"],
    }
