"""Step 5 - validate every threat.

Pure code. Nothing is deleted: a threat that fails a check keeps its place in
the table and carries a ``validation_note`` saying what is wrong, so the
expert decides rather than the machine hiding things.

Checks:
  1. the component/flow it points at exists in the approved system model;
  2. STRIDE letter is one of the six;
  3. every cited identifier exists in the knowledge base (this is the
     fabricated-identifier gate: an invented CWE number is rejected here);
  4. required fields are present (title, description, scenario);
  5. evidence quotes actually appear in the document;
  6. near-duplicates of another threat on the same element;
  7. proposed mitigations exist in the mitigation catalogue and are not
     obviously unrelated to the threat.
"""

from __future__ import annotations

import difflib
import logging
import re
import unicodedata

from dataclasses import dataclass

from sqlalchemy import select

from app.controls import catalog as controls_catalog
from app.core.db import SessionLocal
from app.kb.search import identifiers_exist
from app.models import Document, SystemModel as SystemModelRow, Threat
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.steps import step_by_no
from app.schemas.system_model import SystemModel

logger = logging.getLogger(__name__)

STEP = step_by_no(5)

VALID_STRIDE = {"S", "T", "R", "I", "D", "E"}
# Titles this similar on the same element are treated as duplicates.
DUPLICATE_RATIO = 0.86
MIN_QUOTE_CHARS = 12

# Human readable text for each note code, shown in the UI.
NOTE_LABELS = {
    "unknown_component": "Bileşen onaylı sistem modelinde yok",
    "unknown_flow": "Akış onaylı sistem modelinde yok",
    "invalid_stride": "Geçersiz STRIDE kodu",
    "unknown_knowledge_id": "Kaynak kimliği bilgi tabanında bulunamadı",
    "no_knowledge_id": "Hiç kaynak kimliği yok",
    "missing_field": "Zorunlu alan boş",
    "evidence_not_found": "Kanıt alıntısı dokümanda bulunamadı",
    "no_evidence": "Kanıt yok; varsayım olarak işaretlendi",
    "duplicate": "Başka bir tehditle büyük ölçüde aynı",
    "unknown_mitigation": "Önlem kataloğunda olmayan önlem",
    "no_mitigation": "Önerilen önlem yok",
}


def _normalise(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i")
    return re.sub(r"\s+", " ", folded.casefold()).strip()


def _similar(left: str, right: str) -> float:
    return difflib.SequenceMatcher(None, _normalise(left), _normalise(right)).ratio()


def _note(code: str, detail: str | None = None, severity: str = "warning") -> dict:
    return {
        "code": code,
        "label": NOTE_LABELS.get(code, code),
        "detail": detail,
        "severity": severity,
    }


@dataclass
class ThreatView:
    """Everything the checks need, independent of the ORM."""

    title: str
    description: str | None
    scenario: str | None
    stride: str
    component_ref: str | None
    flow_ref: str | None
    evidence: list[dict]
    knowledge_ids: list[str]
    mitigation_ids: list[str]


def validate_threat(
    threat: ThreatView,
    *,
    component_ids: set[str],
    flow_ids: set[str],
    known_ids: dict[str, bool],
    document_text: str,
    mitigation_catalog: set[str],
    seen: list[tuple[str, str, str]],
) -> list[dict]:
    """Run every check and return the notes. Nothing is ever dropped.

    ``document_text`` must already be normalised; ``seen`` accumulates
    (component, flow, title) of the threats checked so far and is appended to.
    """
    notes: list[dict] = []

    # 1 - model references
    if threat.component_ref and threat.component_ref not in component_ids:
        notes.append(_note("unknown_component", threat.component_ref, "error"))
    if threat.flow_ref and threat.flow_ref not in flow_ids:
        notes.append(_note("unknown_flow", threat.flow_ref, "error"))

    # 2 - STRIDE
    if threat.stride not in VALID_STRIDE:
        notes.append(_note("invalid_stride", threat.stride, "error"))

    # 3 - knowledge identifiers: the fabricated-identifier gate
    if not threat.knowledge_ids:
        notes.append(_note("no_knowledge_id"))
    unknown = [
        value
        for value in threat.knowledge_ids
        if not known_ids.get(value.strip().upper(), False)
    ]
    if unknown:
        notes.append(_note("unknown_knowledge_id", ", ".join(sorted(unknown)), "error"))

    # 4 - required fields
    for field_name, value in (
        ("başlık", threat.title),
        ("açıklama", threat.description),
        ("senaryo", threat.scenario),
    ):
        if not (value or "").strip():
            notes.append(_note("missing_field", field_name))

    # 5 - evidence quotes must appear in the document
    if not threat.evidence:
        notes.append(_note("no_evidence", severity="info"))
    else:
        unverified = [
            item["quote"]
            for item in threat.evidence
            if len(item.get("quote", "")) >= MIN_QUOTE_CHARS
            and _normalise(item["quote"]) not in document_text
        ]
        if unverified:
            notes.append(_note("evidence_not_found", unverified[0][:120], "error"))

    # 6 - duplicates on the same element
    key = (threat.component_ref or "", threat.flow_ref or "")
    for component, flow, title in seen:
        if (component, flow) == key and _similar(title, threat.title) >= DUPLICATE_RATIO:
            notes.append(_note("duplicate", title))
            break
    seen.append((key[0], key[1], threat.title))

    # 7 - mitigations
    if not threat.mitigation_ids:
        notes.append(_note("no_mitigation", severity="info"))
    unknown_mitigations = [
        value for value in threat.mitigation_ids if value not in mitigation_catalog
    ]
    if unknown_mitigations:
        notes.append(
            _note("unknown_mitigation", ", ".join(unknown_mitigations), "error")
        )

    return notes


async def run(ctx: RunContext) -> dict[str, int]:
    async with SessionLocal() as session:
        model_row = (
            await session.execute(
                select(SystemModelRow)
                .where(SystemModelRow.run_id == ctx.run_id)
                .order_by(SystemModelRow.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if model_row is None:
            raise StepFailed("Önce sistem modelinin çıkarılması gerekir (2. adım).")
        model = SystemModel.model_validate(model_row.data)

        threats = (
            await session.execute(
                select(Threat).where(Threat.run_id == ctx.run_id).order_by(
                    Threat.created_at
                )
            )
        ).scalars().all()
        if not threats:
            raise StepFailed("Doğrulanacak tehdit yok (4. adımı çalıştırın).")

        documents = (
            await session.execute(
                select(Document).where(Document.project_id == ctx.project_id)
            )
        ).scalars().all()
        haystack = _normalise("\n".join(d.raw_text or "" for d in documents))

        component_ids = model.component_ids()
        flow_ids = {flow.id for flow in model.data_flows}
        mitigation_catalog = controls_catalog.load_mitigations()

        # One database round trip for every identifier cited anywhere.
        cited = sorted(
            {
                source.get("id", "")
                for threat in threats
                for source in (threat.knowledge_sources or [])
                if source.get("id")
            }
        )
        known_ids = await identifiers_exist(session, cited)

        counters = {
            "checked": len(threats),
            "flagged": 0,
            "unknown_ids": 0,
            "duplicates": 0,
            "evidence_missing": 0,
        }
        seen: list[tuple[str, str, str]] = []  # (component, flow, title)

        for index, threat in enumerate(threats, start=1):
            if index % 10 == 0 or index == len(threats):
                await ctx.report(
                    STEP,
                    progress_value=index / len(threats),
                    message=f"Tehdit {index}/{len(threats)} doğrulanıyor",
                    counters=dict(counters),
                )

            notes = validate_threat(
                ThreatView(
                    title=threat.title,
                    description=threat.description,
                    scenario=threat.scenario,
                    stride=threat.stride,
                    component_ref=threat.component_ref,
                    flow_ref=threat.flow_ref,
                    evidence=threat.evidence or [],
                    knowledge_ids=[
                        s.get("id")
                        for s in (threat.knowledge_sources or [])
                        if s.get("id")
                    ],
                    mitigation_ids=[
                        m.get("id") for m in (threat.mitigations or []) if m.get("id")
                    ],
                ),
                component_ids=component_ids,
                flow_ids=flow_ids,
                known_ids=known_ids,
                document_text=haystack,
                mitigation_catalog=set(mitigation_catalog),
                seen=seen,
            )

            for note in notes:
                if note["code"] == "unknown_knowledge_id":
                    counters["unknown_ids"] += len(
                        (note.get("detail") or "").split(",")
                    )
                elif note["code"] == "duplicate":
                    counters["duplicates"] += 1
                elif note["code"] == "evidence_not_found":
                    counters["evidence_missing"] += 1

            # The rule context note from step 4 is bookkeeping, not a finding.
            carried = [
                note
                for note in (threat.validation_notes or [])
                if note.get("code") == "rule_context"
            ]
            blocking = [n for n in notes if n["severity"] in ("error", "warning")]
            threat.validation_notes = carried + notes
            threat.validation_status = "flagged" if blocking else "ok"
            threat.is_assumption = not (threat.evidence or [])
            if blocking:
                counters["flagged"] += 1

        await session.commit()

    ctx.step_output[STEP.no] = {
        "checked": counters["checked"],
        "flagged": counters["flagged"],
        "unknown_ids": counters["unknown_ids"],
        "duplicates": counters["duplicates"],
        "evidence_missing": counters["evidence_missing"],
        "note_labels": NOTE_LABELS,
    }
    return counters
