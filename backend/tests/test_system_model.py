"""The SystemModel schema, merging and the code-side post-processing."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.pipeline.step2_system_model import _chunk, _post_process
from app.schemas.system_model import SystemModel, merge_models


def _model(**overrides) -> dict:
    base = {
        "components": [
            {
                "id": "api",
                "name": "API Geçidi",
                "type": "gateway",
                "internet_facing": True,
                "evidence": [{"quote": "API Geçidi tüm istekleri karşılar", "page": 1}],
            },
            {
                "id": "db",
                "name": "İşlem Veritabanı",
                "type": "database",
                "evidence": [{"quote": "İşlem Veritabanı kayıtları tutar", "page": 2}],
            },
        ],
        "data_flows": [
            {
                "id": "f1",
                "source_id": "api",
                "target_id": "db",
                "protocol": "TLS",
                "encrypted": True,
                "evidence": [{"quote": "API Geçidi tüm istekleri karşılar", "page": 1}],
            }
        ],
    }
    base.update(overrides)
    return base


def test_unknown_is_accepted_where_the_document_is_silent() -> None:
    model = SystemModel.model_validate(_model())
    assert model.components[1].internet_facing == "unknown"
    assert model.data_flows[0].authenticated == "unknown"


def test_invalid_component_type_is_rejected() -> None:
    payload = _model()
    payload["components"][0]["type"] = "kuantum_servis"
    with pytest.raises(ValidationError):
        SystemModel.model_validate(payload)


def test_dangling_flows_are_detected() -> None:
    payload = _model()
    payload["data_flows"][0]["target_id"] = "yok-boyle-bir-bilesen"
    model = SystemModel.model_validate(payload)
    assert [f.id for f in model.dangling_flows()] == ["f1"]


def test_post_process_drops_dangling_flows_and_records_an_assumption() -> None:
    payload = _model()
    payload["data_flows"][0]["target_id"] = "yok"
    model = SystemModel.model_validate(payload)

    stats = _post_process(model, "API Geçidi tüm istekleri karşılar")

    assert model.data_flows == []
    assert stats["dropped_flows"] == 1
    assert any("çıkarıldı" in a.text for a in model.assumptions)


def test_post_process_flags_a_quote_that_is_not_in_the_document() -> None:
    payload = _model()
    payload["components"][0]["evidence"] = [
        {"quote": "Bu cümle dokümanda hiç geçmiyor efendim", "page": 1}
    ]
    model = SystemModel.model_validate(payload)

    stats = _post_process(
        model,
        "API Geçidi tüm istekleri karşılar\nİşlem Veritabanı kayıtları tutar",
    )

    # Only the invented quote is flagged; the real ones pass.
    assert stats["evidence_unverified"] == 1
    assert stats["evidence_checked"] == 3
    assert "bulunamadı" in (model.components[0].evidence[0].section or "")


def test_post_process_accepts_a_quote_with_different_spacing_and_case() -> None:
    payload = _model()
    payload["components"][0]["evidence"] = [
        {"quote": "api   geçidi TÜM istekleri karşılar", "page": 1}
    ]
    model = SystemModel.model_validate(payload)

    stats = _post_process(
        model, "API Geçidi tüm istekleri karşılar\nİşlem Veritabanı kayıtları tutar"
    )

    assert stats["evidence_unverified"] == 0


def test_components_without_evidence_are_reported_as_assumptions() -> None:
    payload = _model()
    payload["components"][1]["evidence"] = []
    model = SystemModel.model_validate(payload)

    stats = _post_process(model, "API Geçidi tüm istekleri karşılar")

    assert stats["without_evidence"] == 1
    assert any("varsayım" in a.text.lower() for a in model.assumptions)


def test_merge_keeps_both_evidence_quotes_for_a_repeated_component() -> None:
    first = SystemModel.model_validate(
        {
            "components": [
                {
                    "id": "api",
                    "name": "API Geçidi",
                    "type": "gateway",
                    "evidence": [{"quote": "ilk alıntı", "page": 1}],
                }
            ]
        }
    )
    second = SystemModel.model_validate(
        {
            "components": [
                {
                    "id": "api",
                    "name": "API Geçidi",
                    "type": "gateway",
                    "technology": "Kong",
                    "evidence": [{"quote": "ikinci alıntı", "page": 2}],
                }
            ]
        }
    )

    merged = merge_models([first, second])

    assert len(merged.components) == 1
    assert len(merged.components[0].evidence) == 2
    # A field the first chunk left blank is filled from the second.
    assert merged.components[0].technology == "Kong"


def test_chunking_splits_on_page_markers_only() -> None:
    text = "[Sayfa 1]\n" + "a" * 100 + "\n[Sayfa 2]\n" + "b" * 100

    chunks = _chunk(text, 150)

    assert len(chunks) == 2
    assert chunks[0].startswith("[Sayfa 1]")
    assert chunks[1].startswith("[Sayfa 2]")


def test_short_text_is_not_chunked() -> None:
    assert _chunk("kısa metin", 1000) == ["kısa metin"]
