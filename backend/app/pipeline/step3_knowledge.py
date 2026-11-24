"""Step 3 - gather relevant knowledge for every component and flow.

Pure code: hybrid retrieval over the knowledge base (full-text + vector,
merged with RRF). The result is stored on the step so the panel can show,
per component, which sources were retrieved and why.
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.core.db import SessionLocal
from app.kb.document_search import search_document
from app.kb.search import search as hybrid_search
from app.models import SystemModel as SystemModelRow
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.steps import step_by_no
from app.schemas.system_model import SystemModel

logger = logging.getLogger(__name__)

STEP = step_by_no(3)

# How many sources to keep per model element.
PER_ELEMENT = 6
# Passages of the document itself kept per component or flow.
PASSAGES_PER_ELEMENT = 3
# Sources that describe controls rather than threats; kept out of the
# threat-generation context so the model is not nudged into "fix" language.
CONTROL_SOURCES = {"iso27001", "nist80053", "asvs", "tr_regulation"}

# Retrieved knowledge, kept for step 4 within the same run.
_retrieved: dict[str, dict] = {}


def take_retrieved(run_id: str) -> dict:
    return _retrieved.pop(run_id, {})


def _component_query(component) -> str:
    parts = [
        component.name,
        component.type,
        component.technology or "",
        component.description or "",
    ]
    if component.internet_facing is True:
        parts.append("internete açık")
    if component.authentication:
        parts.append(component.authentication)
    return " ".join(part for part in parts if part)[:600]


def _flow_query(flow, names: dict[str, str]) -> str:
    parts = [
        names.get(flow.source_id, flow.source_id),
        names.get(flow.target_id, flow.target_id),
        flow.protocol or "",
        " ".join(flow.data_classes),
        flow.description or "",
    ]
    if flow.encrypted is False:
        parts.append("şifrelenmemiş trafik")
    if flow.authenticated is False:
        parts.append("kimlik doğrulaması olmayan çağrı")
    return " ".join(part for part in parts if part)[:600]


async def run(ctx: RunContext) -> dict[str, int]:
    async with SessionLocal() as session:
        row = (
            await session.execute(
                select(SystemModelRow)
                .where(SystemModelRow.run_id == ctx.run_id)
                .order_by(SystemModelRow.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            raise StepFailed("Önce sistem modelinin çıkarılması gerekir (2. adım).")
        model = SystemModel.model_validate(row.data)

        names = {component.id: component.name for component in model.components}
        elements: list[tuple[str, str, str, str]] = [
            ("component", component.id, component.name, _component_query(component))
            for component in model.components
        ] + [
            (
                "flow",
                flow.id,
                f"{names.get(flow.source_id, flow.source_id)} → "
                f"{names.get(flow.target_id, flow.target_id)}",
                _flow_query(flow, names),
            )
            for flow in model.data_flows
        ]

        if not elements:
            raise StepFailed("Sistem modelinde bileşen veya akış yok.")

        results: list[dict] = []
        all_ids: set[str] = set()
        degraded = False
        total_passages = 0

        for index, (kind, element_id, label, query) in enumerate(elements, start=1):
            await ctx.report(
                STEP,
                progress_value=index / len(elements),
                message=f"Bilgi tabanında arama {index}/{len(elements)}: {label}",
                counters={"queries": index, "sources": len(all_ids)},
            )
            hits, diagnostics = await hybrid_search(
                session, query, limit=PER_ELEMENT
            )
            if diagnostics.get("mode") != "hybrid":
                degraded = True
            sources = [hit.as_dict() for hit in hits]
            all_ids.update(hit.identifier for hit in hits)

            # The same question, asked of the document itself: which
            # passages talk about this component? Step 4 uses these when
            # the document is too long to hand over whole.
            passages = await search_document(
                session, ctx.project_id, query, limit=PASSAGES_PER_ELEMENT
            )
            total_passages += len(passages)

            results.append(
                {
                    "kind": kind,
                    "id": element_id,
                    "label": label,
                    "query": query,
                    "sources": sources,
                    "passages": [hit.as_dict() for hit in passages],
                }
            )

    payload = {
        "elements": results,
        "passages": total_passages,
        "unique_identifiers": sorted(all_ids),
        "degraded": degraded,
        "note": (
            "Vektör araması kullanılamadı; yalnızca anahtar kelime eşleşmesi "
            "yapıldı."
            if degraded
            else None
        ),
    }
    _retrieved[ctx.run_id] = payload
    ctx.step_output[STEP.no] = payload

    return {
        "queries": len(elements),
        "sources": len(all_ids),
        "passages": total_passages,
        "per_element": PER_ELEMENT,
    }
