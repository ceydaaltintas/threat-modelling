"""Step 4 - generate threats.

Two independent producers, then a merge:

  (a) the YAML rule catalogue, which runs without an LLM and always produces
      the same findings for the same model;
  (b) the LLM, which gets the retrieved knowledge and the document and is
      asked for threats specific to *this* system.

The merge is code: near-duplicate titles on the same element collapse into a
single ``merged`` threat that keeps both sources' evidence. If the LLM is
unavailable or out of quota the step still completes with the rule findings
and says plainly that the LLM part was skipped - the demo must not die with
the quota.
"""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata

from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.llm.base import LLMError
from app.llm.prompts import load_prompt
from app.models import Document, SystemModel as SystemModelRow, Threat
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.step3_knowledge import take_retrieved
from app.pipeline.steps import step_by_no
from app.rules.engine import RuleThreat, evaluate
from app.schemas.system_model import SystemModel
from app.schemas.threats import LlmThreat, LlmThreatList

logger = logging.getLogger(__name__)

STEP = step_by_no(4)
PROMPT_NAME = "threat_generation.v1"

# Titles this similar, on the same element, are treated as the same threat.
DUPLICATE_RATIO = 0.82
# Document text handed to the model; the system model carries the structure.
MAX_DOCUMENT_CHARS = 18_000
MAX_KNOWLEDGE_BLOCKS = 40
# Retrieved knowledge is the other half of this prompt; without a cap a
# broad document can push the whole request past the provider's limit.
MAX_KNOWLEDGE_CHARS = 24_000


def _normalise(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", folded.casefold()).strip()


def _similar(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, _normalise(left), _normalise(right)).ratio()


def _model_summary(model: SystemModel) -> str:
    lines = ["Bileşenler:"]
    for component in model.components:
        lines.append(
            f"- id={component.id} | {component.name} | tür={component.type} | "
            f"teknoloji={component.technology or 'belirtilmemiş'} | "
            f"bölge={component.trust_zone or 'belirtilmemiş'} | "
            f"internete açık={component.internet_facing}"
        )
    names = {component.id: component.name for component in model.components}
    lines.append("Veri akışları:")
    for flow in model.data_flows:
        lines.append(
            f"- id={flow.id} | {names.get(flow.source_id, flow.source_id)} → "
            f"{names.get(flow.target_id, flow.target_id)} | "
            f"protokol={flow.protocol or 'belirtilmemiş'} | "
            f"şifreli={flow.encrypted} | kimlik doğrulamalı={flow.authenticated} | "
            f"veri={', '.join(flow.data_classes) or 'belirtilmemiş'}"
        )
    if model.unknowns:
        lines.append("Dokümanda belirtilmemiş konular:")
        lines.extend(f"- {item.text}" for item in model.unknowns)
    return "\n".join(lines)


def _knowledge_blocks(retrieved: dict) -> tuple[str, set[str]]:
    """Render retrieved sources as <knowledge id="..."> blocks."""
    seen: dict[str, str] = {}
    for element in retrieved.get("elements", []):
        for source in element.get("sources", []):
            seen.setdefault(
                source["identifier"],
                f'<knowledge id="{source["identifier"]}" source="{source["source"]}">'
                f'{source["title"]}. {source["text"]}</knowledge>',
            )
            if len(seen) >= MAX_KNOWLEDGE_BLOCKS:
                break
    return "\n".join(seen.values()), set(seen)


def _rule_threat_rows(threats: list[RuleThreat]) -> list[dict]:
    return [
        {
            "source": "rule",
            "rule_id": threat.rule_id,
            "component_ref": threat.component_ref,
            "flow_ref": threat.flow_ref,
            "stride": threat.stride,
            "title": threat.title,
            "description": threat.description,
            "scenario": threat.scenario,
            "evidence": threat.evidence,
            "knowledge_sources": [{"id": kid} for kid in threat.knowledge_ids],
            "mitigations": [{"id": mid} for mid in threat.mitigations],
            "ai_proposed": None,
            "rule_context": {
                "base_likelihood": threat.base_likelihood,
                "base_impact": threat.base_impact,
                "confidence": threat.confidence,
                "internet_facing": threat.context.internet_facing,
                "sensitive_data": threat.context.sensitive_data,
                "data_classes": threat.context.data_classes,
                "control_evidence": threat.context.control_evidence,
                "context_adjust": threat.context_adjust,
                "area": threat.area,
            },
            "is_assumption": not threat.evidence,
        }
        for threat in threats
    ]


def _llm_threat_rows(
    threats: list[LlmThreat], model: SystemModel, allowed_ids: set[str]
) -> tuple[list[dict], dict[str, int]]:
    """Convert LLM output, dropping references the model does not contain."""
    component_ids = model.component_ids()
    flow_ids = {flow.id for flow in model.data_flows}
    rows: list[dict] = []
    dropped_component = 0
    dropped_ids = 0

    for threat in threats:
        component_ref = threat.component_id
        if component_ref and component_ref not in component_ids:
            dropped_component += 1
            component_ref = None
        flow_ref = threat.flow_id if threat.flow_id in flow_ids else None

        kept_ids = [kid for kid in threat.knowledge_ids if kid in allowed_ids]
        dropped_ids += len(threat.knowledge_ids) - len(kept_ids)

        rows.append(
            {
                "source": "llm",
                "rule_id": None,
                "component_ref": component_ref,
                "flow_ref": flow_ref,
                "stride": threat.stride,
                "title": threat.title,
                "description": threat.description,
                "scenario": threat.scenario,
                "evidence": [item.model_dump(mode="json") for item in threat.evidence],
                "knowledge_sources": [{"id": kid} for kid in kept_ids],
                "mitigations": [],
                "ai_proposed": {
                    "likelihood": threat.likelihood,
                    "impact": threat.impact,
                    "rationale": threat.rationale,
                },
                "rule_context": None,
                "is_assumption": not threat.evidence,
            }
        )

    return rows, {
        "dropped_component_refs": dropped_component,
        "dropped_knowledge_ids": dropped_ids,
    }


def _merge(rule_rows: list[dict], llm_rows: list[dict]) -> tuple[list[dict], int]:
    """Collapse near-duplicate titles on the same element into one threat."""
    merged = list(rule_rows)
    duplicates = 0

    for candidate in llm_rows:
        match = None
        for existing in merged:
            same_element = (
                existing["component_ref"] == candidate["component_ref"]
                and existing["flow_ref"] == candidate["flow_ref"]
            )
            if not same_element:
                continue
            if _similar(existing["title"], candidate["title"]) >= DUPLICATE_RATIO:
                match = existing
                break
        if match is None:
            merged.append(candidate)
            continue

        duplicates += 1
        match["source"] = "merged"
        match["evidence"] = (match["evidence"] or []) + (candidate["evidence"] or [])
        known = {item["id"] for item in match["knowledge_sources"]}
        match["knowledge_sources"].extend(
            item for item in candidate["knowledge_sources"] if item["id"] not in known
        )
        match["ai_proposed"] = candidate["ai_proposed"]
        if candidate["scenario"] and len(candidate["scenario"]) > len(
            match["scenario"] or ""
        ):
            match["scenario"] = candidate["scenario"]
        match["is_assumption"] = not match["evidence"]

    return merged, duplicates


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

        documents = (
            await session.execute(
                select(Document)
                .where(Document.project_id == ctx.project_id)
                .order_by(Document.created_at)
            )
        ).scalars().all()
        document_text = "\n".join(d.raw_text or "" for d in documents)

    # --- (a) rules ---
    await ctx.report(
        STEP, progress_value=0.15, message="Kural kataloğu çalıştırılıyor"
    )
    rule_threats = evaluate(model, document_text)
    rule_rows = _rule_threat_rows(rule_threats)
    await ctx.report(
        STEP,
        progress_value=0.35,
        message=f"Kural kataloğu {len(rule_rows)} tehdit üretti",
        counters={"rule_threats": len(rule_rows), "threats": len(rule_rows)},
    )

    # --- (b) LLM ---
    retrieved = take_retrieved(ctx.run_id) or ctx.step_output.get(3, {})
    knowledge_text, allowed_ids = _knowledge_blocks(retrieved)
    llm_rows: list[dict] = []
    llm_note: str | None = None
    llm_stats: dict[str, int] = {}

    if ctx.gateway is None:
        llm_note = (
            "LLM sağlayıcısı yapılandırılmadığı için bağlama özel tehdit "
            "önerisi üretilmedi; yalnızca kural kataloğu çalıştı."
        )
    else:
        await ctx.report(
            STEP,
            progress_value=0.5,
            message="Bağlama özel tehditler öneriliyor (LLM)",
            counters={"rule_threats": len(rule_rows), "threats": len(rule_rows)},
        )
        prompt = load_prompt(PROMPT_NAME)
        known = "\n".join(f"- {item['title']}" for item in rule_rows) or "(yok)"
        summary = _model_summary(model)

        def _build(doc_chars: int, knowledge_chars: int) -> str:
            return prompt.render(
                system_model=summary,
                known_threats=known,
                knowledge_blocks=knowledge_text[:knowledge_chars]
                or "(kaynak getirilemedi)",
                document_text=document_text[:doc_chars],
            )

        user = _build(MAX_DOCUMENT_CHARS, MAX_KNOWLEDGE_CHARS)

        def _shrink(budget: int) -> str:
            # The system model and the rule findings are what the step is
            # reasoning about, so the document excerpt and the retrieved
            # knowledge give way first - in that order.
            fixed = len(_build(0, 0))
            room = max(0, budget - fixed)
            return _build(int(room * 0.6), int(room * 0.4))
        try:
            async def _waiting(attempt: int, delay: float) -> None:
                await ctx.report(
                    STEP,
                    progress_value=0.5,
                    message=(
                        f"Model yoğun; {int(delay)} sn sonra yeniden denenecek "
                        f"({attempt}. deneme)"
                    ),
                )

            result = await ctx.gateway.generate_json(
                prompt_name=PROMPT_NAME,
                system=prompt.system,
                user=user,
                schema=LlmThreatList,
                step_no=STEP.no,
                on_wait=_waiting,
                shrink_user=_shrink,
            )
            llm_rows, llm_stats = _llm_threat_rows(result.threats, model, allowed_ids)
        except LLMError as exc:
            # The quota running out must not lose the rule findings.
            logger.warning("LLM tehdit üretimi atlandı: %s", exc.message)
            llm_note = f"LLM tehdit önerisi alınamadı: {exc.message}"

    # --- (c) merge ---
    await ctx.report(
        STEP,
        progress_value=0.85,
        message="Kural ve LLM tehditleri birleştiriliyor",
    )
    merged, duplicates = _merge(rule_rows, llm_rows)

    async with SessionLocal() as session:
        # A retry of this step replaces its own output.
        await session.execute(delete(Threat).where(Threat.run_id == ctx.run_id))
        for item in merged:
            session.add(
                Threat(
                    run_id=ctx.run_id,
                    source=item["source"],
                    rule_id=item["rule_id"],
                    component_ref=item["component_ref"],
                    flow_ref=item["flow_ref"],
                    stride=item["stride"],
                    title=item["title"],
                    description=item["description"],
                    scenario=item["scenario"],
                    evidence=item["evidence"],
                    knowledge_sources=item["knowledge_sources"],
                    ai_proposed=item["ai_proposed"],
                    mitigations=item["mitigations"],
                    # Risk and validation run in later steps.
                    system_calc=None,
                    validation_status="not_run",
                    review_status="pending",
                    is_assumption=item["is_assumption"],
                    validation_notes=(
                        [{"code": "rule_context", "data": item["rule_context"]}]
                        if item["rule_context"]
                        else None
                    ),
                )
            )
        await session.commit()

    ctx.step_output[STEP.no] = {
        "rule_threats": len(rule_rows),
        "llm_threats": len(llm_rows),
        "merged_duplicates": duplicates,
        "total": len(merged),
        "llm_note": llm_note,
        "llm_stats": llm_stats,
        "knowledge_ids_offered": len(allowed_ids),
    }

    return {
        "rule_threats": len(rule_rows),
        "llm_threats": len(llm_rows),
        "merged": duplicates,
        "threats": len(merged),
    }
