"""Assemble everything a report needs, in one place.

Reports must say the same thing whatever the format, so PDF, Excel and JSON
all start from this structure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AnalysisRun,
    Document,
    Project,
    SystemModel as SystemModelRow,
    Threat,
)
from app.schemas.review import ACTION_LABELS  # noqa: F401 - used by callers
from app.schemas.system_model import SystemModel

LEVEL_ORDER = {"Kritik": 0, "Yüksek": 1, "Orta": 2, "Düşük": 3}

# Threats the expert rejected or called a false positive are listed
# separately rather than counted in the headline numbers.
EXCLUDED_REVIEW = {"rejected", "false_positive"}


@dataclass
class ReportData:
    project_name: str
    run_id: str
    generated_at: datetime
    documents: list[dict]
    model: SystemModel
    threats: list[Threat]
    counts: dict[str, int]
    by_level: dict[str, int]
    by_stride: dict[str, int]
    by_component: list[tuple[str, int]]
    heatmap: dict[str, int]
    thresholds: dict[str, int]
    top_threats: list[Threat] = field(default_factory=list)
    excluded: list[Threat] = field(default_factory=list)
    unknowns: list[dict] = field(default_factory=list)
    assumptions: list[dict] = field(default_factory=list)
    summary_text: str | None = None
    summary_is_ai: bool = False
    llm_settings: dict | None = None
    demo_replay: str = "false"

    def component_name(self, component_id: str | None) -> str:
        if not component_id:
            return "Sistem geneli"
        for component in self.model.components:
            if component.id == component_id:
                return component.name
        return component_id

    def level_of(self, threat: Threat) -> str:
        expert = threat.expert or {}
        if expert.get("level"):
            return expert["level"]
        return (threat.system_calc or {}).get("level") or "—"

    def score_of(self, threat: Threat) -> int:
        expert = threat.expert or {}
        if expert.get("score"):
            return int(expert["score"])
        return int((threat.system_calc or {}).get("score") or 0)


async def collect(session: AsyncSession, run_id: str) -> ReportData:
    run = await session.get(AnalysisRun, run_id)
    if run is None:
        raise ValueError("Analiz bulunamadı.")
    project = await session.get(Project, run.project_id)

    documents = (
        await session.execute(
            select(Document)
            .where(Document.project_id == run.project_id)
            .order_by(Document.created_at)
        )
    ).scalars().all()

    model_row = (
        await session.execute(
            select(SystemModelRow)
            .where(SystemModelRow.run_id == run_id)
            .order_by(SystemModelRow.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    model = (
        SystemModel.model_validate(model_row.data) if model_row else SystemModel()
    )

    threats = (
        await session.execute(
            select(Threat).where(Threat.run_id == run_id).order_by(Threat.created_at)
        )
    ).scalars().all()

    data = ReportData(
        project_name=project.name if project else "Adsız proje",
        run_id=run_id,
        generated_at=datetime.now(tz=timezone.utc),
        documents=[
            {
                "filename": d.filename,
                "pages": d.page_count,
                "type": d.doc_type,
            }
            for d in documents
        ],
        model=model,
        threats=threats,
        counts={},
        by_level={},
        by_stride={},
        by_component=[],
        heatmap={},
        thresholds={},
        llm_settings=run.llm_settings,
        demo_replay=run.demo_replay,
    )

    included = [t for t in threats if t.review_status not in EXCLUDED_REVIEW]
    data.excluded = [t for t in threats if t.review_status in EXCLUDED_REVIEW]

    for threat in included:
        level = data.level_of(threat)
        data.by_level[level] = data.by_level.get(level, 0) + 1
        data.by_stride[threat.stride] = data.by_stride.get(threat.stride, 0) + 1
        name = data.component_name(threat.component_ref)
        calc = threat.system_calc or {}
        if calc.get("likelihood") and calc.get("impact"):
            key = f"{calc['likelihood']}x{calc['impact']}"
            data.heatmap[key] = data.heatmap.get(key, 0) + 1

    per_component: dict[str, int] = {}
    for threat in included:
        name = data.component_name(threat.component_ref)
        per_component[name] = per_component.get(name, 0) + 1
    data.by_component = sorted(
        per_component.items(), key=lambda item: -item[1]
    )[:10]

    review_counts: dict[str, int] = {}
    for threat in threats:
        review_counts[threat.review_status] = (
            review_counts.get(threat.review_status, 0) + 1
        )
    data.counts = {
        "total": len(threats),
        "included": len(included),
        "excluded": len(data.excluded),
        "assumptions": sum(1 for t in included if t.is_assumption),
        "flagged": sum(1 for t in included if t.validation_status == "flagged"),
        "accepted": review_counts.get("accepted", 0),
        "edited": review_counts.get("edited", 0),
        "rejected": review_counts.get("rejected", 0),
        "false_positive": review_counts.get("false_positive", 0),
        "pending": review_counts.get("pending", 0),
        "components": len(model.components),
        "flows": len(model.data_flows),
    }

    data.top_threats = sorted(
        included,
        key=lambda t: (LEVEL_ORDER.get(data.level_of(t), 9), -data.score_of(t)),
    )[:5]
    data.unknowns = [item.model_dump(mode="json") for item in model.unknowns]
    data.assumptions = [item.model_dump(mode="json") for item in model.assumptions]
    return data
