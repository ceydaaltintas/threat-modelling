"""Excel export: every threat with its evidence, sources and decision."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from app.reports.data import LEVEL_ORDER, ReportData
from app.reports.pdf import REVIEW_LABELS, STRIDE_LABELS

HEADER_FILL = PatternFill("solid", fgColor="1E3A5F")
HEADER_FONT = Font(color="FFFFFF", bold=True)

LEVEL_FILL = {
    "Kritik": PatternFill("solid", fgColor="F6D5DE"),
    "Yüksek": PatternFill("solid", fgColor="FAE2D2"),
    "Orta": PatternFill("solid", fgColor="FBF0CF"),
    "Düşük": PatternFill("solid", fgColor="D8EBE4"),
}

COLUMNS = [
    ("Seviye", 10),
    ("Skor", 6),
    ("Olasılık", 9),
    ("Etki", 7),
    ("Tehdit", 52),
    ("Bileşen", 26),
    ("Akış", 18),
    ("STRIDE", 9),
    ("STRIDE açıklaması", 20),
    ("Kaynak türü", 13),
    ("Kural", 22),
    ("Kaynak kimlikleri", 28),
    ("Kanıt alıntısı", 48),
    ("Kanıt sayfası", 12),
    ("Varsayım mı", 12),
    ("Doğrulama", 12),
    ("Doğrulama notları", 36),
    ("Risk kırılımı", 54),
    ("AI önerisi", 14),
    ("Uzman kararı", 14),
    ("Uzman notu", 32),
    ("Önlemler", 46),
    ("Kontrol eşlemeleri", 40),
]


def _autosize(sheet) -> None:
    for index, (_, width) in enumerate(COLUMNS, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def build_workbook(data: ReportData) -> bytes:
    workbook = Workbook()

    # --- threats ---
    sheet = workbook.active
    sheet.title = "Tehditler"
    sheet.append([name for name, _ in COLUMNS])
    for cell in sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    sheet.freeze_panes = "A2"
    _autosize(sheet)

    ordered = sorted(
        data.threats,
        key=lambda t: (LEVEL_ORDER.get(data.level_of(t), 9), -data.score_of(t)),
    )
    for threat in ordered:
        calc = threat.system_calc or {}
        expert = threat.expert or {}
        ai = threat.ai_proposed or {}
        evidence = threat.evidence or []
        row = [
            data.level_of(threat),
            data.score_of(threat),
            calc.get("likelihood"),
            calc.get("impact"),
            threat.title,
            data.component_name(threat.component_ref),
            threat.flow_ref or "",
            threat.stride,
            STRIDE_LABELS.get(threat.stride, ""),
            {"rule": "Kural", "llm": "AI", "merged": "Kural + AI"}.get(
                threat.source, threat.source
            ),
            threat.rule_id or "",
            ", ".join(s.get("id", "") for s in (threat.knowledge_sources or [])),
            evidence[0].get("quote", "") if evidence else "",
            evidence[0].get("page", "") if evidence else "",
            "Evet" if threat.is_assumption else "Hayır",
            {"ok": "Geçti", "flagged": "İşaretli", "not_run": "Çalışmadı"}.get(
                threat.validation_status, threat.validation_status
            ),
            "; ".join(
                note.get("label", note.get("code", ""))
                for note in (threat.validation_notes or [])
                if note.get("code") != "rule_context"
            ),
            calc.get("explanation", ""),
            f"O{ai['likelihood']} × E{ai['impact']}"
            if ai.get("likelihood") and ai.get("impact")
            else "",
            REVIEW_LABELS.get(threat.review_status, threat.review_status),
            expert.get("note") or expert.get("reason") or "",
            "; ".join(
                f"{m.get('id')}: {m.get('title', '')}"
                for m in (threat.mitigations or [])
            ),
            "; ".join(
                f"{m.get('framework')} {m.get('id')}"
                + (" (doğrulanacak)" if m.get("verification") == "needed" else "")
                for m in (threat.control_mappings or [])
            ),
        ]
        sheet.append(row)
        fill = LEVEL_FILL.get(data.level_of(threat))
        if fill:
            sheet.cell(row=sheet.max_row, column=1).fill = fill
        for column in (5, 13, 17, 18, 21, 22, 23):
            sheet.cell(row=sheet.max_row, column=column).alignment = Alignment(
                wrap_text=True, vertical="top"
            )

    # --- summary ---
    summary = workbook.create_sheet("Özet")
    summary.column_dimensions["A"].width = 34
    summary.column_dimensions["B"].width = 60
    rows = [
        ("Proje", data.project_name),
        ("Analiz kimliği", data.run_id),
        ("Rapor tarihi", data.generated_at.isoformat()),
        ("Doküman", ", ".join(d["filename"] for d in data.documents)),
        ("Bileşen", data.counts["components"]),
        ("Veri akışı", data.counts["flows"]),
        ("", ""),
        ("Toplam tehdit", data.counts["total"]),
        ("Rapora dahil", data.counts["included"]),
        ("Uzmanın elediği", data.counts["excluded"]),
        ("Varsayım", data.counts["assumptions"]),
        ("Doğrulamada işaretli", data.counts["flagged"]),
        ("Karar bekleyen", data.counts["pending"]),
        ("", ""),
    ]
    for level in ("Kritik", "Yüksek", "Orta", "Düşük"):
        rows.append((level, data.by_level.get(level, 0)))
    rows.append(("", ""))
    for code in "STRIDE":
        rows.append(
            (f"{code} — {STRIDE_LABELS[code]}", data.by_stride.get(code, 0))
        )
    rows.append(("", ""))
    rows.append(
        (
            "Uyarı",
            "Bu tehditler dokümandan türetilen olasılıklardır; sistem testi "
            "yapılmadan kesin kabul edilmemelidir.",
        )
    )
    for label, value in rows:
        summary.append([label, value])
    summary["B" + str(summary.max_row)].alignment = Alignment(wrap_text=True)
    for cell in summary["A"]:
        cell.font = Font(bold=True)

    # --- system model ---
    model_sheet = workbook.create_sheet("Sistem modeli")
    model_sheet.append(
        ["Tür", "Kimlik", "Ad", "Teknoloji", "Güven bölgesi", "İnternete açık", "Kanıt"]
    )
    for cell in model_sheet[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for column, width in zip("ABCDEFG", (10, 24, 30, 26, 22, 14, 50)):
        model_sheet.column_dimensions[column].width = width
    for component in data.model.components:
        model_sheet.append(
            [
                "Bileşen",
                component.id,
                component.name,
                component.technology or "",
                component.trust_zone or "",
                {True: "Evet", False: "Hayır"}.get(
                    component.internet_facing, "Belirtilmemiş"
                ),
                component.evidence[0].quote if component.evidence else "",
            ]
        )
    for flow in data.model.data_flows:
        model_sheet.append(
            [
                "Akış",
                flow.id,
                f"{data.component_name(flow.source_id)} → "
                f"{data.component_name(flow.target_id)}",
                flow.protocol or "",
                ", ".join(flow.data_classes),
                {True: "Şifreli", False: "Şifresiz"}.get(
                    flow.encrypted, "Belirtilmemiş"
                ),
                flow.evidence[0].quote if flow.evidence else "",
            ]
        )

    # --- open questions ---
    gaps = workbook.create_sheet("Açık konular")
    gaps.append(["Tür", "Konu", "Not"])
    for cell in gaps[1]:
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
    for column, width in zip("ABC", (18, 70, 50)):
        gaps.column_dimensions[column].width = width
    for item in data.unknowns:
        gaps.append(["Belirtilmemiş", item.get("text", ""), item.get("impact", "")])
    for item in data.assumptions:
        gaps.append(["Varsayım", item.get("text", ""), item.get("reason", "")])

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
