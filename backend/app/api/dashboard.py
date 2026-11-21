"""Dashboard data for a single run.

Everything here is computed from the stored threats, so the dashboard can
never drift from the threat table or the report.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_session
from app.models import AnalysisRun, Project, SystemModel, Threat
from app.schemas.system_model import SystemModel as SystemModelSchema

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

LEVEL_ORDER = {"Kritik": 0, "Yüksek": 1, "Orta": 2, "Düşük": 3}
EXCLUDED_REVIEW = {"rejected", "false_positive"}


@router.get("")
async def dashboard(
    run_id: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Summary for one run; defaults to the most recent finished one."""
    if run_id:
        run = await session.get(AnalysisRun, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Analiz bulunamadı.")
    else:
        run = (
            await session.execute(
                select(AnalysisRun)
                .where(AnalysisRun.status.in_(("done", "waiting_user")))
                .order_by(AnalysisRun.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if run is None:
            return {"available": False, "reason": "Henüz tamamlanmış analiz yok."}

    project = await session.get(Project, run.project_id)
    settings = get_settings()

    threats = (
        await session.execute(select(Threat).where(Threat.run_id == run.id))
    ).scalars().all()
    if not threats:
        return {
            "available": False,
            "reason": "Bu analiz için henüz tehdit üretilmedi.",
            "run": {"id": run.id, "project": project.name if project else None},
        }

    model_row = (
        await session.execute(
            select(SystemModel)
            .where(SystemModel.run_id == run.id)
            .order_by(SystemModel.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    model = (
        SystemModelSchema.model_validate(model_row.data)
        if model_row
        else SystemModelSchema()
    )
    names = {component.id: component.name for component in model.components}

    def level_of(threat: Threat) -> str:
        expert = threat.expert or {}
        return expert.get("level") or (threat.system_calc or {}).get("level") or "—"

    def score_of(threat: Threat) -> int:
        expert = threat.expert or {}
        return int(expert.get("score") or (threat.system_calc or {}).get("score") or 0)

    included = [t for t in threats if t.review_status not in EXCLUDED_REVIEW]

    by_level: dict[str, int] = {}
    by_stride: dict[str, int] = {}
    by_component: dict[str, int] = {}
    by_review: dict[str, int] = {}
    heatmap: dict[str, int] = {}

    for threat in threats:
        by_review[threat.review_status] = by_review.get(threat.review_status, 0) + 1
    for threat in included:
        level = level_of(threat)
        by_level[level] = by_level.get(level, 0) + 1
        by_stride[threat.stride] = by_stride.get(threat.stride, 0) + 1
        name = names.get(threat.component_ref or "", "Sistem geneli")
        by_component[name] = by_component.get(name, 0) + 1
        calc = threat.system_calc or {}
        if calc.get("likelihood") and calc.get("impact"):
            key = f"{calc['likelihood']}x{calc['impact']}"
            heatmap[key] = heatmap.get(key, 0) + 1

    top = sorted(
        included, key=lambda t: (LEVEL_ORDER.get(level_of(t), 9), -score_of(t))
    )[:5]

    decided = sum(
        by_review.get(status, 0)
        for status in ("accepted", "rejected", "false_positive", "edited")
    )

    return {
        "available": True,
        "run": {
            "id": run.id,
            "project": project.name if project else "Adsız proje",
            "status": run.status,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
        },
        "kpis": {
            "total": len(threats),
            "included": len(included),
            "critical": by_level.get("Kritik", 0),
            "high": by_level.get("Yüksek", 0),
            "assumptions": sum(1 for t in included if t.is_assumption),
            "flagged": sum(1 for t in included if t.validation_status == "flagged"),
            "decided": decided,
            "decided_ratio": round(decided / len(threats), 3) if threats else 0,
            "components": len(model.components),
            "flows": len(model.data_flows),
        },
        "by_level": by_level,
        "by_stride": by_stride,
        "by_component": sorted(
            by_component.items(), key=lambda item: -item[1]
        )[:10],
        "by_review": by_review,
        "heatmap": heatmap,
        "thresholds": {
            "low": settings.risk_threshold_low,
            "medium": settings.risk_threshold_medium,
            "high": settings.risk_threshold_high,
        },
        "top_threats": [
            {
                "id": t.id,
                "title": t.title,
                "level": level_of(t),
                "score": score_of(t),
                "component": names.get(t.component_ref or "", "Sistem geneli"),
                "stride": t.stride,
            }
            for t in top
        ],
        "unknowns": [item.model_dump(mode="json") for item in model.unknowns],
    }


@router.get("/runs")
async def dashboard_runs(session: AsyncSession = Depends(get_session)) -> list[dict]:
    """Runs that have threats, newest first, for the dashboard's picker."""
    rows = (
        await session.execute(
            select(
                AnalysisRun.id,
                AnalysisRun.created_at,
                AnalysisRun.status,
                Project.name,
                func.count(Threat.id),
            )
            .join(Project, Project.id == AnalysisRun.project_id)
            .outerjoin(Threat, Threat.run_id == AnalysisRun.id)
            .group_by(AnalysisRun.id, Project.name)
            .having(func.count(Threat.id) > 0)
            .order_by(AnalysisRun.created_at.desc())
            .limit(25)
        )
    ).all()
    return [
        {
            "id": run_id,
            "created_at": created_at,
            "status": status,
            "project": name,
            "threats": count,
        }
        for run_id, created_at, status, name, count in rows
    ]
