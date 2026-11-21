"""Step 5 validation. Nothing is dropped; everything suspicious is flagged."""

from __future__ import annotations

import pytest

from app.pipeline.step5_validation import (
    NOTE_LABELS,
    ThreatView,
    _normalise,
    validate_threat,
)

DOCUMENT = _normalise(
    "Transfer Servisi limit kontrolünü çağırır. İç ağda servisler arası "
    "trafik HTTP üzerinden akar. Operasyon Paneli ortak hesapla kullanılır."
)

COMPONENTS = {"transfer-servisi", "limit-servisi"}
FLOWS = {"f-transfer-limit"}
MITIGATIONS = {"M-AUTHZ-OBJECT", "M-RATE-LIMIT"}
KNOWN_IDS = {"CWE-639": True, "API1:2023": True, "CWE-99999": False}


def view(**overrides) -> ThreatView:
    base = {
        "title": "Nesne düzeyi yetki kontrolü eksikliği",
        "description": "Açıklama metni.",
        "scenario": "Saldırgan nesne kimliğini değiştirir.",
        "stride": "E",
        "component_ref": "transfer-servisi",
        "flow_ref": None,
        "evidence": [{"quote": "Transfer Servisi limit kontrolünü çağırır", "page": 1}],
        "knowledge_ids": ["CWE-639"],
        "mitigation_ids": ["M-AUTHZ-OBJECT"],
    }
    base.update(overrides)
    return ThreatView(**base)


def check(threat: ThreatView, seen: list | None = None) -> list[dict]:
    return validate_threat(
        threat,
        component_ids=COMPONENTS,
        flow_ids=FLOWS,
        known_ids=KNOWN_IDS,
        document_text=DOCUMENT,
        mitigation_catalog=MITIGATIONS,
        seen=seen if seen is not None else [],
    )


def codes(notes: list[dict]) -> set[str]:
    return {note["code"] for note in notes}


def test_a_well_formed_threat_produces_no_notes() -> None:
    assert check(view()) == []


# --- the fabricated identifier gate (docs/PROMPT.md, phase 3 acceptance) ---


def test_invented_knowledge_identifier_is_rejected() -> None:
    """A CWE number that is not in the knowledge base must be flagged."""
    notes = check(view(knowledge_ids=["CWE-99999"]))
    assert "unknown_knowledge_id" in codes(notes)
    note = next(n for n in notes if n["code"] == "unknown_knowledge_id")
    assert note["severity"] == "error"
    assert "CWE-99999" in note["detail"]


def test_a_mix_of_real_and_invented_identifiers_flags_only_the_invented_one() -> None:
    notes = check(view(knowledge_ids=["CWE-639", "CWE-99999"]))
    note = next(n for n in notes if n["code"] == "unknown_knowledge_id")
    assert note["detail"] == "CWE-99999"


def test_identifier_match_ignores_case_and_spacing() -> None:
    assert check(view(knowledge_ids=[" cwe-639 "])) == []


def test_threat_without_any_source_is_flagged() -> None:
    assert "no_knowledge_id" in codes(check(view(knowledge_ids=[])))


# --- model references ------------------------------------------------


def test_component_not_in_the_model_is_flagged() -> None:
    notes = check(view(component_ref="hayali-servis"))
    assert "unknown_component" in codes(notes)


def test_flow_not_in_the_model_is_flagged() -> None:
    assert "unknown_flow" in codes(check(view(flow_ref="f-yok")))


def test_system_level_threat_without_component_is_fine() -> None:
    assert check(view(component_ref=None)) == []


# --- STRIDE and required fields --------------------------------------


def test_invalid_stride_letter_is_flagged() -> None:
    assert "invalid_stride" in codes(check(view(stride="X")))


@pytest.mark.parametrize("field", ["title", "description", "scenario"])
def test_missing_required_field_is_flagged(field: str) -> None:
    assert "missing_field" in codes(check(view(**{field: ""})))


# --- evidence ---------------------------------------------------------


def test_quote_that_is_not_in_the_document_is_flagged() -> None:
    notes = check(
        view(evidence=[{"quote": "Bu cümle dokümanda kesinlikle geçmiyor", "page": 1}])
    )
    assert "evidence_not_found" in codes(notes)


def test_quote_matching_with_different_case_and_spacing_passes() -> None:
    assert check(
        view(evidence=[{"quote": "TRANSFER   servisi limit kontrolünü çağırır"}])
    ) == []


def test_threat_without_evidence_is_noted_as_an_assumption() -> None:
    notes = check(view(evidence=[]))
    note = next(n for n in notes if n["code"] == "no_evidence")
    # Informational: an assumption is allowed, it just has to be visible.
    assert note["severity"] == "info"


# --- duplicates -------------------------------------------------------


def test_near_duplicate_on_the_same_component_is_flagged() -> None:
    seen: list = []
    check(view(), seen)
    notes = check(view(title="Nesne duzeyi yetki kontrolu eksikligi"), seen)
    assert "duplicate" in codes(notes)


def test_same_title_on_a_different_component_is_not_a_duplicate() -> None:
    seen: list = []
    check(view(), seen)
    notes = check(view(component_ref="limit-servisi"), seen)
    assert "duplicate" not in codes(notes)


# --- mitigations ------------------------------------------------------


def test_mitigation_outside_the_catalogue_is_flagged() -> None:
    notes = check(view(mitigation_ids=["M-UYDURMA"]))
    assert "unknown_mitigation" in codes(notes)


def test_threat_without_mitigations_is_noted() -> None:
    assert "no_mitigation" in codes(check(view(mitigation_ids=[])))


# --- reporting --------------------------------------------------------


def test_every_note_code_has_a_turkish_label() -> None:
    notes = check(
        view(
            component_ref="yok",
            stride="X",
            knowledge_ids=["CWE-99999"],
            evidence=[],
            mitigation_ids=["M-UYDURMA"],
            description="",
        )
    )
    assert notes
    for note in notes:
        assert note["label"] == NOTE_LABELS[note["code"]]
        assert note["severity"] in {"error", "warning", "info"}
