"""Threat endpoints for the step 4-8 table."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.service import record as audit_record
from app.core.config import get_settings
from app.core.db import get_session
from app.models import AnalysisRun, Threat
from app.risk import Thresholds
from app.schemas.review import (
    ACTION_STATUS,
    BulkReviewRequest,
    ReviewRequest,
)

router = APIRouter(prefix="/api/runs/{run_id}/threats", tags=["threats"])

# Demo-only identity, same headers the runs router uses.
DEMO_ACTOR_HEADER = "x-demo-actor"
DEMO_ROLE_HEADER = "x-demo-role"


def _actor(request: Request) -> tuple[str, str]:
    actor = request.headers.get(DEMO_ACTOR_HEADER) or "demo@ornekbanka.local"
    role = request.headers.get(DEMO_ROLE_HEADER) or "security_expert"
    return actor, role


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
    review: str | None = Query(default=None),
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
    if review:
        stmt = stmt.where(Threat.review_status == review)

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
    by_review = dict(
        (
            await session.execute(
                select(Threat.review_status, func.count())
                .where(Threat.run_id == run_id)
                .group_by(Threat.review_status)
            )
        ).all()
    )
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
            "by_review": by_review,
            "assumptions": assumptions,
            "flagged": flagged,
        },
        "threats": [_serialise(threat) for threat in rows],
    }


def _expert_record(
    threat: Threat,
    payload: ReviewRequest,
    *,
    actor: str,
    thresholds: Thresholds,
) -> dict:
    """Build the expert block. Code keeps system_calc untouched."""
    record: dict = {
        "status": ACTION_STATUS[payload.action],
        "by": actor,
        "at": datetime.now(tz=timezone.utc).isoformat(),
        "note": payload.note,
    }
    if payload.action == "edit":
        computed = threat.system_calc or {}
        likelihood = payload.likelihood or computed.get("likelihood") or 3
        impact = payload.impact or computed.get("impact") or 3
        score = likelihood * impact
        record.update(
            {
                "likelihood": likelihood,
                "impact": impact,
                "score": score,
                "level": thresholds.level_for(score),
                "reason": payload.reason,
            }
        )
    return record


@router.post("/{threat_id}/review")
async def review_threat(
    run_id: str,
    threat_id: str,
    payload: ReviewRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Record one expert decision. Every call lands in the audit trail."""
    actor, role = _actor(request)
    if role == "manager":
        raise HTTPException(
            status_code=403,
            detail="Yönetici rolü salt okunurdur; karar veremez.",
        )

    threat = await session.get(Threat, threat_id)
    if threat is None or threat.run_id != run_id:
        raise HTTPException(status_code=404, detail="Tehdit bulunamadı.")

    settings = get_settings()
    thresholds = Thresholds(
        low=settings.risk_threshold_low,
        medium=settings.risk_threshold_medium,
        high=settings.risk_threshold_high,
    )

    old = {
        "review_status": threat.review_status,
        "expert": threat.expert,
    }
    if payload.action == "reset":
        threat.expert = None
    else:
        threat.expert = _expert_record(
            threat, payload, actor=actor, thresholds=thresholds
        )
    threat.review_status = ACTION_STATUS[payload.action]

    await audit_record(
        session,
        actor=actor,
        actor_role=role,
        action=f"threat_{payload.action}",
        object_type="threat",
        object_id=threat.id,
        run_id=run_id,
        old_value=old,
        new_value={
            "review_status": threat.review_status,
            "expert": threat.expert,
            "title": threat.title,
        },
        reason=payload.reason or payload.note,
    )
    await session.commit()
    await session.refresh(threat)
    return _serialise(threat)


@router.post("/review-bulk")
async def review_threats_bulk(
    run_id: str,
    payload: BulkReviewRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Apply one decision to several threats; each gets its own audit row."""
    actor, role = _actor(request)
    if role == "manager":
        raise HTTPException(
            status_code=403,
            detail="Yönetici rolü salt okunurdur; karar veremez.",
        )

    rows = (
        await session.execute(
            select(Threat).where(
                Threat.run_id == run_id, Threat.id.in_(payload.threat_ids)
            )
        )
    ).scalars().all()
    if not rows:
        raise HTTPException(status_code=404, detail="Seçilen tehdit bulunamadı.")

    status = ACTION_STATUS[payload.action]
    now = datetime.now(tz=timezone.utc).isoformat()
    for threat in rows:
        old = {"review_status": threat.review_status, "expert": threat.expert}
        threat.expert = (
            None
            if payload.action == "reset"
            else {
                "status": status,
                "by": actor,
                "at": now,
                "note": payload.note,
                "bulk": True,
            }
        )
        threat.review_status = status
        await audit_record(
            session,
            actor=actor,
            actor_role=role,
            action=f"threat_{payload.action}",
            object_type="threat",
            object_id=threat.id,
            run_id=run_id,
            old_value=old,
            new_value={"review_status": status, "title": threat.title},
            reason=payload.note,
        )

    await session.commit()
    return {"updated": len(rows), "review_status": status}
