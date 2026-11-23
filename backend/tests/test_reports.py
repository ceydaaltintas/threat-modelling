"""Report generation: PDF, Excel and the JSON exports."""

from __future__ import annotations

def _pdf_text(pdf_bytes: bytes) -> str:
    """The report's text, read back with the same library the app uses."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(pdf_bytes)
    try:
        pages = []
        for page in document:
            textpage = page.get_textpage()
            try:
                pages.append(textpage.get_text_bounded() or "")
            finally:
                textpage.close()
            page.close()
        return "\n".join(pages)
    finally:
        document.close()

import json
from datetime import datetime, timezone
from io import BytesIO

import pytest

from app.reports import excel as excel_report
from app.reports import json_export
from app.reports import pdf as pdf_report
from app.reports.data import ReportData
from app.reports.storage import ALLOWED, report_path
from app.schemas.system_model import SystemModel
from tests.fixtures.mobile_transfer_model import MOBILE_TRANSFER_MODEL


class FakeThreat:
    """Stands in for the ORM row; reports only read attributes."""

    def __init__(self, **kwargs):
        defaults = {
            "id": "t1",
            "source": "rule",
            "rule_id": "R-API-BOLA",
            "component_ref": "transfer-servisi",
            "flow_ref": None,
            "stride": "E",
            "title": "Nesne düzeyi yetki kontrolü eksikliği",
            "description": "Açıklama.",
            "scenario": "Saldırgan nesne kimliğini değiştirir.",
            "evidence": [{"quote": "Transfer Servisi doğrular", "page": 1}],
            "knowledge_sources": [{"id": "CWE-639"}, {"id": "API1:2023"}],
            "ai_proposed": {"likelihood": 4, "impact": 5, "rationale": "AI gerekçesi"},
            "system_calc": {
                "likelihood": 4,
                "impact": 5,
                "score": 20,
                "level": "Kritik",
                "base_likelihood": 3,
                "base_impact": 5,
                "breakdown": [],
                "explanation": "Olasılık 3 + 1 = 4; Etki 5 = 5. Skor 20 → Kritik.",
            },
            "expert": None,
            "mitigations": [
                {"id": "M-AUTHZ-OBJECT", "title": "Nesne düzeyi yetki kontrolü",
                 "text": "Sunucuda doğrulayın.", "effort": "orta"}
            ],
            "control_mappings": [
                {"framework": "ISO 27001:2022", "id": "A.5.15",
                 "verification": "needed", "via": "M-AUTHZ-OBJECT"}
            ],
            "validation_notes": [],
            "validation_status": "ok",
            "review_status": "pending",
            "is_assumption": False,
        }
        defaults.update(kwargs)
        for key, value in defaults.items():
            setattr(self, key, value)


def make_data(threats: list[FakeThreat] | None = None) -> ReportData:
    model = SystemModel.model_validate(MOBILE_TRANSFER_MODEL)
    threats = threats if threats is not None else [FakeThreat()]
    data = ReportData(
        project_name="Mobil Bankacılık – Para Transferi",
        run_id="run-1",
        generated_at=datetime(2026, 11, 21, 12, 0, tzinfo=timezone.utc),
        documents=[{"filename": "01_mobil.pdf", "pages": 2, "type": "pdf"}],
        model=model,
        threats=threats,
        counts={
            "total": len(threats),
            "included": len(threats),
            "excluded": 0,
            "assumptions": 0,
            "flagged": 0,
            "accepted": 0,
            "edited": 0,
            "rejected": 0,
            "false_positive": 0,
            "pending": len(threats),
            "components": len(model.components),
            "flows": len(model.data_flows),
        },
        by_level={"Kritik": len(threats)},
        by_stride={"E": len(threats)},
        by_component=[("Transfer Servisi", len(threats))],
        heatmap={"4x5": len(threats)},
        thresholds={"low": 4, "medium": 9, "high": 16},
        llm_settings={"provider": "gemini_native", "model": "x"},
    )
    data.top_threats = threats[:5]
    data.unknowns = [{"text": "Yedek şifrelemesi belirtilmemiş", "impact": None}]
    data.assumptions = [{"text": "Varsayım", "reason": "test"}]
    return data


# --- PDF ---------------------------------------------------------------


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return pdf_report.render_pdf(make_data())


def test_pdf_is_produced(pdf_bytes: bytes) -> None:
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 5000


def test_pdf_renders_turkish_characters(pdf_bytes: bytes) -> None:
    """The acceptance criterion: Turkish characters must come out right."""
    text = _pdf_text(pdf_bytes)

    for probe in [
        "Tehdit Modelleme Raporu",
        "Yönetici özeti",
        "Risk dağılımı",
        "olasılıklardır",
        "Dokümanda belirtilmemiş",
    ]:
        assert probe in text, probe
    # No replacement characters or mojibake.
    assert "�" not in text


def test_pdf_states_the_disclaimer(pdf_bytes: bytes) -> None:
    # The sentence wraps across lines in the layout, so compare on
    # whitespace-normalised text.
    text = " ".join(_pdf_text(pdf_bytes).split())
    assert "sistem testi yapılmadan kesin kabul edilmemelidir" in text


def test_pdf_marks_iso_mappings_for_verification(pdf_bytes: bytes) -> None:
    text = _pdf_text(pdf_bytes)
    assert "doğrulanacak" in text


def test_ai_summary_is_labelled() -> None:
    data = make_data()
    data.summary_text = "Yapay zekâ ile yazılmış özet metni."
    data.summary_is_ai = True
    text = _pdf_text(pdf_report.render_pdf(data))
    assert "AI üretti" in text


def test_html_escapes_document_content() -> None:
    """A quote from the document cannot inject markup into the report."""
    threat = FakeThreat(title="<script>alert(1)</script> kötü başlık")
    html = pdf_report.render_html(make_data([threat]))
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_rejected_threats_are_listed_separately() -> None:
    data = make_data()
    data.excluded = [FakeThreat(id="t2", review_status="rejected",
                                title="Elenen bulgu")]
    html = pdf_report.render_html(data)
    assert "Uzmanın elediği bulgular" in html
    assert "Elenen bulgu" in html


# --- Excel -------------------------------------------------------------


def test_excel_has_the_expected_sheets() -> None:
    from openpyxl import load_workbook

    workbook = load_workbook(BytesIO(excel_report.build_workbook(make_data())))
    assert workbook.sheetnames == [
        "Tehditler",
        "Özet",
        "Sistem modeli",
        "Açık konular",
    ]


def test_excel_threat_row_carries_evidence_and_sources() -> None:
    from openpyxl import load_workbook

    workbook = load_workbook(BytesIO(excel_report.build_workbook(make_data())))
    sheet = workbook["Tehditler"]
    headers = [cell.value for cell in sheet[1]]
    row = {headers[i]: cell.value for i, cell in enumerate(sheet[2])}

    assert row["Seviye"] == "Kritik"
    assert row["Skor"] == 20
    assert "CWE-639" in row["Kaynak kimlikleri"]
    assert row["Kanıt alıntısı"] == "Transfer Servisi doğrular"
    assert "doğrulanacak" in row["Kontrol eşlemeleri"]
    assert "Olasılık" in row["Risk kırılımı"]


def test_excel_summary_sheet_carries_the_disclaimer() -> None:
    from openpyxl import load_workbook

    workbook = load_workbook(BytesIO(excel_report.build_workbook(make_data())))
    values = [
        cell.value
        for row in workbook["Özet"].iter_rows()
        for cell in row
        if isinstance(cell.value, str)
    ]
    assert any("olasılıklardır" in value for value in values)


# --- JSON --------------------------------------------------------------


def test_native_json_round_trips() -> None:
    payload = json.loads(
        json.dumps(json_export.build_native(make_data()), ensure_ascii=False)
    )
    assert payload["format"] == "threat-modelling-platform/v1"
    assert payload["threats"][0]["system_calc"]["score"] == 20
    assert payload["threats"][0]["evidence"]
    assert "olasılıklardır" in payload["disclaimer"]


def test_native_json_keeps_ai_and_system_values_apart() -> None:
    payload = json_export.build_native(make_data())
    threat = payload["threats"][0]
    assert threat["ai_proposed"]["likelihood"] == 4
    assert threat["system_calc"]["likelihood"] == 4
    assert "skora girmez" in payload["notes"]["scoring"]


def test_otm_export_has_the_core_sections() -> None:
    payload = json_export.build_otm(make_data())
    assert payload["otmVersion"] == json_export.OTM_VERSION
    assert payload["project"]["name"]
    assert payload["components"]
    assert payload["dataflows"]
    assert payload["threats"][0]["categories"] == ["Elevation of Privilege"]
    assert payload["threats"][0]["cwes"] == ["639"]


def test_otm_components_reference_existing_trust_zones() -> None:
    payload = json_export.build_otm(make_data())
    zone_ids = {zone["id"] for zone in payload["trustZones"]}
    for component in payload["components"]:
        parent = component.get("parent", {}).get("trustZone")
        if parent:
            assert parent in zone_ids


def test_otm_dataflow_endpoints_are_known_components() -> None:
    payload = json_export.build_otm(make_data())
    ids = {component["id"] for component in payload["components"]}
    for flow in payload["dataflows"]:
        assert flow["source"] in ids
        assert flow["destination"] in ids


# --- storage -----------------------------------------------------------


def test_only_known_report_names_are_served() -> None:
    assert set(ALLOWED) == {
        "rapor.pdf",
        "tehditler.xlsx",
        "analiz.json",
        "otm.json",
    }


def test_path_traversal_is_refused() -> None:
    assert report_path("run-1", "../../etc/passwd") is None
    assert report_path("run-1", "rapor.pdf.exe") is None


# --- executive summary guard ------------------------------------------


@pytest.mark.parametrize(
    "answer",
    [
        '{"components": [{"id": "c1"}]}',
        "```json\n{\"a\": 1}\n```",
        "<html><body>özet</body></html>",
        "kısa",
        '{"a": 1, "b": 2}',
    ],
)
def test_non_prose_summary_is_rejected(answer: str) -> None:
    """A model that answers with JSON must not end up in the report."""
    from app.pipeline.step9_report import _looks_like_prose

    assert _looks_like_prose(answer) is False


def test_a_real_summary_is_accepted() -> None:
    from app.pipeline.step9_report import _looks_like_prose

    summary = (
        "Mobil bankacılık para transferi için yapılan tehdit modelleme "
        "çalışmasında on iki bileşen incelendi ve kırk üç bulgu üretildi. "
        "En çok dikkat isteyen konular kimlik doğrulama ve iç ağ trafiğinin "
        "şifrelenmesidir. Önerilen sonraki adım, bulguların sistem testiyle "
        "doğrulanmasıdır."
    )
    assert _looks_like_prose(summary) is True
