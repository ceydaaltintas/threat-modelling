"""Threat endpoints for the step 4-8 table."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.models import AnalysisRun, Threat

router = APIRouter(prefix="/api/runs/{run_id}/threats", tags=["threats"])


def _serialise(threat: Threat) -> dict:
    # The rule context is kept with the validation notes; surface it
    # separately so the UI never has to dig through internal bookkeeping.
    rule_context = None
    notes = []
    for note in threat.validation_notes or []:
        if note.get("code") == "rule_context":
            rule_context = note.get("data")
        else:
            notes.append(note)

    return {
        "id": threat.id,
        "source": threat.source,
        "rule_id": threat.rule_id,
        "component_ref": threat.component_ref,
        "flow_ref": threat.flow_ref,
        "stride": threat.stride,
        "title": threat.title,
        "description": threat.description,
        "scenario": threat.scenario,
        "evidence": threat.evidence or [],
        "knowledge_sources": threat.knowledge_sources or [],
        "ai_proposed": threat.ai_proposed,
        "system_calc": threat.system_calc,
        "expert": threat.expert,
        "mitigations": threat.mitigations or [],
        "control_mappings": threat.control_mappings or [],
        "validation_notes": notes,
        "validation_status": threat.validation_status,
        "review_status": threat.review_status,
        "is_assumption": threat.is_assumption,
        "rule_context": rule_context,
        "created_at": threat.created_at,
    }


@router.get("")
async def list_threats(
    run_id: str,
    stride: str | None = Query(default=None),
    source: str | None = Query(default=None),
    component: str | None = Query(default=None),
    level: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    run = await session.get(AnalysisRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Analiz bulunamadı.")

    stmt = select(Threat).where(Threat.run_id == run_id).order_by(Threat.created_at)
    if stride:
        stmt = stmt.where(Threat.stride == stride)
    if source:
        stmt = stmt.where(Threat.source == source)
    if component:
        stmt = stmt.where(Threat.component_ref == component)
    if level:
        stmt = stmt.where(Threat.system_calc["level"].as_string() == level)

    rows = (await session.execute(stmt)).scalars().all()

    by_source = dict(
        (
            await session.execute(
                select(Threat.source, func.count())
                .where(Threat.run_id == run_id)
                .group_by(Threat.source)
            )
        ).all()
    )
    by_stride = dict(
        (
            await session.execute(
                select(Threat.stride, func.count())
                .where(Threat.run_id == run_id)
                .group_by(Threat.stride)
            )
        ).all()
    )
    assumptions = (
        await session.execute(
            select(func.count())
            .select_from(Threat)
            .where(Threat.run_id == run_id, Threat.is_assumption.is_(True))
        )
    ).scalar_one()
    flagged = (
        await session.execute(
            select(func.count())
            .select_from(Threat)
            .where(Threat.run_id == run_id, Threat.validation_status == "flagged")
        )
    ).scalar_one()
    # One shared expression so SELECT and GROUP BY render identically.
    level = Threat.system_calc["level"].as_string().label("level")
    by_level = {
        name: count
        for name, count in (
            await session.execute(
                select(level, func.count())
                .where(Threat.run_id == run_id)
                .group_by(level)
            )
        ).all()
        if name
    }

    return {
        "total": len(rows),
        "summary": {
            "by_source": by_source,
            "by_stride": by_stride,
            "by_level": by_level,
            "assumptions": assumptions,
            "flagged": flagged,
        },
        "threats": [_serialise(threat) for threat in rows],
    }
