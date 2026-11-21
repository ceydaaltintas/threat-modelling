"""PDF executive report.

Built as HTML and rendered with WeasyPrint. The DejaVu font family is
installed in the image, so Turkish characters (ÇĞİÖŞÜ çğıöşü) render
correctly - there is a test that asserts this.

The report is deliberately plain: a manager should be able to read it
without the product in front of them.
"""

from __future__ import annotations

import html
from datetime import timezone, timedelta

from app.reports.data import LEVEL_ORDER, ReportData

TR = timezone(timedelta(hours=3))

LEVEL_COLOURS = {
    "Kritik": "#b3123a",
    "Yüksek": "#c25a10",
    "Orta": "#b07d0a",
    "Düşük": "#2f6f5b",
}

STRIDE_LABELS = {
    "S": "Kimlik taklidi",
    "T": "Veri değiştirme",
    "R": "İnkâr",
    "I": "Bilgi sızması",
    "D": "Hizmet kesintisi",
    "E": "Yetki yükseltme",
}

REVIEW_LABELS = {
    "pending": "Bekliyor",
    "accepted": "Kabul",
    "rejected": "Reddedildi",
    "false_positive": "Yanlış pozitif",
    "edited": "Düzenlendi",
}

DISCLAIMER = (
    "Bu rapordaki tehditler mimari dokümandan türetilen olasılıklardır; "
    "sistem testi yapılmadan kesin kabul edilmemelidir."
)

CSS = """
@page {
  size: A4;
  margin: 18mm 16mm 20mm 16mm;
  @bottom-left {
    content: "Örnek Banka A.Ş. · Dahili · Kurgusal örnek";
    font-size: 7.5pt; color: #6b7280;
  }
  @bottom-right {
    content: "Sayfa " counter(page) " / " counter(pages);
    font-size: 7.5pt; color: #6b7280;
  }
}
body { font-family: "DejaVu Sans", sans-serif; font-size: 9.5pt; color: #1f2937; line-height: 1.45; }
h1 { font-size: 20pt; margin: 0 0 4pt 0; color: #1e3a5f; }
h2 { font-size: 13pt; margin: 18pt 0 6pt 0; color: #1e3a5f;
     border-bottom: 1px solid #d7dde5; padding-bottom: 3pt; }
h3 { font-size: 10.5pt; margin: 12pt 0 4pt 0; color: #1e3a5f; }
p { margin: 0 0 6pt 0; }
.sub { color: #6b7280; font-size: 9pt; }
.cover { margin-bottom: 10pt; }
.meta { width: 100%; border-collapse: collapse; margin-top: 10pt; }
.meta td { padding: 3pt 6pt; border-bottom: 1px solid #eceff3; vertical-align: top; }
.meta td:first-child { color: #6b7280; width: 32%; }
.warn { border: 1px solid #e3b7a0; background: #fdf3ee; padding: 7pt 9pt;
        border-radius: 3pt; font-size: 8.5pt; margin: 10pt 0; }
.ai { border: 1px solid #c3d4e8; background: #f2f7fd; padding: 7pt 9pt;
      border-radius: 3pt; margin: 6pt 0; }
.badge { display: inline-block; padding: 1pt 5pt; border-radius: 8pt;
         font-size: 7.5pt; color: #fff; }
.kpis { width: 100%; border-collapse: separate; border-spacing: 6pt 0; margin: 8pt 0; }
.kpis td { border: 1px solid #dde3ea; border-radius: 3pt; padding: 7pt 9pt;
           width: 25%; vertical-align: top; }
.kpis .n { font-size: 17pt; font-weight: bold; color: #1e3a5f; }
.kpis .l { font-size: 7.5pt; color: #6b7280; }
table.data { width: 100%; border-collapse: collapse; font-size: 8pt; margin-top: 4pt; }
table.data th { background: #f1f4f8; text-align: left; padding: 4pt 5pt;
                border-bottom: 1px solid #d7dde5; font-weight: bold; }
table.data td { padding: 4pt 5pt; border-bottom: 1px solid #eceff3;
                vertical-align: top; }
/* Keep the heat map and each section heading with what follows them. */
table.heat { border-collapse: collapse; font-size: 8pt;
             page-break-inside: avoid; }
h2, h3 { page-break-after: avoid; }
.kpis, .meta, .warn, .ai { page-break-inside: avoid; }
table.data tr { page-break-inside: avoid; }
table.heat td, table.heat th { border: 1px solid #e2e6eb; padding: 4pt 7pt;
                               text-align: center; }
.mono { font-family: "DejaVu Sans Mono", monospace; font-size: 7.5pt; }
.quote { color: #4b5563; font-style: italic; }
ul { margin: 2pt 0 6pt 14pt; padding: 0; }
li { margin-bottom: 2pt; }
.pagebreak { page-break-before: always; }
.footnote { font-size: 7.5pt; color: #6b7280; margin-top: 4pt; }
"""


def esc(value: object) -> str:
    return html.escape(str(value if value is not None else "—"))


def _level_badge(level: str) -> str:
    colour = LEVEL_COLOURS.get(level, "#6b7280")
    return f'<span class="badge" style="background:{colour}">{esc(level)}</span>'


def _kpis(data: ReportData) -> str:
    cells = [
        ("Toplam tehdit", data.counts["included"]),
        ("Kritik", data.by_level.get("Kritik", 0)),
        ("Yüksek", data.by_level.get("Yüksek", 0)),
        ("Uzman kararı verilen", data.counts["accepted"] + data.counts["edited"]),
    ]
    tds = "".join(
        f'<td><div class="n">{value}</div><div class="l">{esc(label)}</div></td>'
        for label, value in cells
    )
    return f'<table class="kpis"><tr>{tds}</tr></table>'


def _heatmap(data: ReportData) -> str:
    rows = []
    header = "<tr><th></th>" + "".join(
        f"<th>{i}</th>" for i in range(1, 6)
    ) + "<th class='l'>Olasılık →</th></tr>"
    rows.append(header)
    for impact in range(5, 0, -1):
        cells = [f"<th>{impact}</th>"]
        for likelihood in range(1, 6):
            count = data.heatmap.get(f"{likelihood}x{impact}", 0)
            score = likelihood * impact
            level = _level_for(score, data.thresholds)
            colour = LEVEL_COLOURS.get(level, "#6b7280")
            shade = "" if count else "opacity:0.25;"
            cells.append(
                f'<td style="background:{colour};color:#fff;{shade}">'
                f"{count or ''}</td>"
            )
        cells.append("<td></td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return (
        '<table class="heat">' + "".join(rows) + "</table>"
        '<p class="footnote">Dikey eksen: etki, yatay eksen: olasılık. '
        "Hücredeki sayı, o kombinasyondaki tehdit sayısıdır.</p>"
    )


def _level_for(score: int, thresholds: dict[str, int]) -> str:
    if score <= thresholds.get("low", 4):
        return "Düşük"
    if score <= thresholds.get("medium", 9):
        return "Orta"
    if score <= thresholds.get("high", 16):
        return "Yüksek"
    return "Kritik"


def _top_threats(data: ReportData) -> str:
    if not data.top_threats:
        return "<p>Raporlanacak tehdit yok.</p>"
    blocks = []
    for index, threat in enumerate(data.top_threats, start=1):
        sources = ", ".join(
            s.get("id", "") for s in (threat.knowledge_sources or [])
        )
        evidence = (threat.evidence or [{}])[0].get("quote") if threat.evidence else None
        mitigations = "".join(
            f"<li>{esc(m.get('title') or m.get('id'))}: {esc(m.get('text'))}</li>"
            for m in (threat.mitigations or [])[:3]
        )
        blocks.append(
            f"""
<h3>{index}. {esc(threat.title)} {_level_badge(data.level_of(threat))}</h3>
<p class="sub">{esc(data.component_name(threat.component_ref))} ·
STRIDE {esc(threat.stride)} ({esc(STRIDE_LABELS.get(threat.stride, ''))}) ·
Skor {data.score_of(threat)}</p>
<p>{esc(threat.description)}</p>
<p><strong>Senaryo:</strong> {esc(threat.scenario)}</p>
{f'<p class="quote">Dokümandan: “{esc(evidence)}”</p>' if evidence else
 '<p class="quote">Dokümandan kanıt alıntısı yok; varsayım olarak değerlendirilmelidir.</p>'}
<p class="footnote">Kaynaklar: {esc(sources) if sources else '—'}</p>
<p><strong>Önerilen önlemler:</strong></p><ul>{mitigations or '<li>—</li>'}</ul>
"""
        )
    return "".join(blocks)


def _threat_table(data: ReportData) -> str:
    rows = []
    ordered = sorted(
        [t for t in data.threats if t.review_status not in ("rejected", "false_positive")],
        key=lambda t: (LEVEL_ORDER.get(data.level_of(t), 9), -data.score_of(t)),
    )
    for threat in ordered:
        sources = ", ".join(s.get("id", "") for s in (threat.knowledge_sources or []))
        rows.append(
            "<tr>"
            f"<td>{_level_badge(data.level_of(threat))}</td>"
            f"<td>{data.score_of(threat)}</td>"
            f"<td>{esc(threat.title)}</td>"
            f"<td>{esc(data.component_name(threat.component_ref))}</td>"
            f"<td>{esc(threat.stride)}</td>"
            f"<td class='mono'>{esc(sources)}</td>"
            f"<td>{esc(REVIEW_LABELS.get(threat.review_status, threat.review_status))}"
            f"{' · varsayım' if threat.is_assumption else ''}</td>"
            "</tr>"
        )
    return (
        '<table class="data">'
        "<thead><tr><th>Seviye</th><th>Skor</th><th>Tehdit</th>"
        "<th>Bileşen</th><th>STRIDE</th><th>Kaynaklar</th><th>Durum</th></tr></thead>"
        f"<tbody>{''.join(rows) or '<tr><td colspan=7>Kayıt yok.</td></tr>'}</tbody>"
        "</table>"
    )


def _list_block(items: list[dict], key: str, secondary: str) -> str:
    if not items:
        return "<p>Kayıt yok.</p>"
    entries = "".join(
        f"<li>{esc(item.get(key))}"
        + (
            f' <span class="sub">({esc(item.get(secondary))})</span>'
            if item.get(secondary)
            else ""
        )
        + "</li>"
        for item in items
    )
    return f"<ul>{entries}</ul>"


def render_html(data: ReportData) -> str:
    local_time = data.generated_at.astimezone(TR).strftime("%d.%m.%Y %H:%M")
    documents = ", ".join(
        f"{d['filename']} ({d['pages'] or '?'} sayfa)" for d in data.documents
    ) or "—"
    llm = data.llm_settings or {}

    summary_block = ""
    if data.summary_text:
        label = (
            '<p class="sub"><strong>AI üretti</strong> — bu özet yapay zekâ ile '
            "taslaklanmıştır; yayımlamadan önce gözden geçirilmelidir.</p>"
            if data.summary_is_ai
            else ""
        )
        summary_block = (
            f'<div class="ai">{label}<p>{esc(data.summary_text)}</p></div>'
        )

    excluded_block = ""
    if data.excluded:
        rows = "".join(
            f"<tr><td>{esc(t.title)}</td>"
            f"<td>{esc(data.component_name(t.component_ref))}</td>"
            f"<td>{esc(REVIEW_LABELS.get(t.review_status, t.review_status))}</td>"
            f"<td>{esc((t.expert or {}).get('note'))}</td></tr>"
            for t in data.excluded
        )
        excluded_block = (
            "<h2>Uzmanın elediği bulgular</h2>"
            '<p class="sub">Bu bulgular yukarıdaki sayılara dahil değildir; '
            "şeffaflık için listelenmiştir.</p>"
            '<table class="data"><thead><tr><th>Tehdit</th><th>Bileşen</th>'
            "<th>Karar</th><th>Not</th></tr></thead>"
            f"<tbody>{rows}</tbody></table>"
        )

    return f"""<!DOCTYPE html>
<html lang="tr"><head><meta charset="utf-8">
<title>Tehdit Modelleme Raporu — {esc(data.project_name)}</title>
<style>{CSS}</style></head><body>

<div class="cover">
  <p class="sub">Örnek Banka A.Ş. · Bilgi Teknolojileri</p>
  <h1>Tehdit Modelleme Raporu</h1>
  <p class="sub">{esc(data.project_name)}</p>
  <table class="meta">
    <tr><td>Rapor tarihi</td><td>{esc(local_time)}</td></tr>
    <tr><td>Analiz kimliği</td><td class="mono">{esc(data.run_id)}</td></tr>
    <tr><td>İncelenen doküman</td><td>{esc(documents)}</td></tr>
    <tr><td>Sistem modeli</td><td>{data.counts['components']} bileşen,
        {data.counts['flows']} veri akışı</td></tr>
    <tr><td>LLM sağlayıcı / model</td>
        <td>{esc(llm.get('provider'))} / {esc(llm.get('model') or 'belirtilmemiş')}
        {' · kayıtlı çıktı modu' if data.demo_replay != 'false' else ''}</td></tr>
  </table>
</div>

<div class="warn">{DISCLAIMER}</div>

<h2>Yönetici özeti</h2>
{summary_block}
{_kpis(data)}
<p>Analiz {data.counts['total']} tehdit üretti. Bunların
{data.counts['included']} tanesi raporda yer alıyor;
{data.counts['excluded']} tanesi uzman tarafından elendi.
{data.counts['assumptions']} bulgu dokümanda doğrudan kanıt bulunmadığı için
<strong>varsayım</strong> olarak işaretlendi,
{data.counts['flagged']} bulgu otomatik doğrulamada işaretlendi.
{data.counts['pending']} bulgu için henüz uzman kararı verilmedi.</p>

<h2>Risk dağılımı</h2>
<table class="data"><thead><tr><th>Seviye</th><th>Adet</th></tr></thead><tbody>
{''.join(f'<tr><td>{_level_badge(level)}</td><td>{data.by_level.get(level, 0)}</td></tr>'
         for level in ['Kritik', 'Yüksek', 'Orta', 'Düşük'])}
</tbody></table>
<h3>Risk ısı haritası</h3>
{_heatmap(data)}

<h3>STRIDE dağılımı</h3>
<table class="data"><thead><tr><th>Kategori</th><th>Adet</th></tr></thead><tbody>
{''.join(f"<tr><td>{code} — {esc(STRIDE_LABELS[code])}</td>"
         f"<td>{data.by_stride.get(code, 0)}</td></tr>" for code in 'STRIDE')}
</tbody></table>

<h3>Bileşen bazlı tehdit sayısı</h3>
<table class="data"><thead><tr><th>Bileşen</th><th>Adet</th></tr></thead><tbody>
{''.join(f'<tr><td>{esc(name)}</td><td>{count}</td></tr>'
         for name, count in data.by_component) or '<tr><td colspan=2>—</td></tr>'}
</tbody></table>

<div class="pagebreak"></div>
<h2>En kritik bulgular</h2>
{_top_threats(data)}

<div class="pagebreak"></div>
<h2>Tüm bulgular</h2>
{_threat_table(data)}

<h2>Dokümanda belirtilmemiş konular</h2>
<p class="sub">Tehdit modellemesi için önemli olduğu hâlde mimari dokümanda
yanıtlanmamış sorular.</p>
{_list_block(data.unknowns, 'text', 'impact')}

<h2>Varsayımlar</h2>
{_list_block(data.assumptions, 'text', 'reason')}

{excluded_block}

<h2>Yöntem ve kaynaklar</h2>
<p>Tehditler iki bağımsız üreticiden gelir: kurum içi YAML kural kataloğu
(LLM'siz, tekrarlanabilir) ve bağlama özel öneriler üreten dil modeli.
Risk puanını <strong>kod</strong> hesaplar; dil modelinin önerdiği değer
yalnızca karşılaştırma için saklanır. Her bulgunun kaynak kimliği bilgi
tabanında doğrulanır; doğrulanamayan kimlik işaretlenir.</p>
<p class="footnote">Kaynaklar: MITRE ATT&amp;CK (Apache-2.0, atıf zorunlu),
MITRE CWE/CAPEC, OWASP Top 10 / API Top 10 / MASVS / LLM Top 10 (CC BY-SA 4.0),
NIST SP 800-53 (kamu malı), OWASP ASVS (CC BY-SA 4.0).
ISO/IEC 27001:2022 ve Türkiye mevzuatı için yalnızca madde kimliği ve bu
projede yazılmış kısa özet kullanılmıştır; madde numaraları
<strong>doğrulanacak</strong> olarak işaretlidir ve kurumun kendi standart
nüshasından teyit edilmelidir.</p>
<div class="warn">{DISCLAIMER}</div>
</body></html>"""


def render_pdf(data: ReportData) -> bytes:
    from weasyprint import HTML

    return HTML(string=render_html(data)).write_pdf()
