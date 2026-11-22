"""Builds the data-flow figure for docs/mimari.html.

Four columns per step: what goes in, what the step does, whether the model
is called (and with what), and what is written where. Every label lives
inside a box rather than floating over an arrow: a swimlane version put the
arrow captions in the 8px gaps between lanes and they landed on top of the
step titles.

WeasyPrint ignores SVG markers, so arrowheads are drawn as triangles.

    python3 docs/_diagram.py        # rewrites the <svg> block in mimari.html
"""

from __future__ import annotations

import pathlib

W = 662
COLS = [("Girdi", 0, 150), ("Adım", 166, 152), ("LLM çağrısı", 334, 158), ("Yazılan", 508, 154)]
HEAD_H = 18
GAP = 11
INK, MUTED, SLATE = "#0f3d6b", "#5b6472", "#64748b"

# (title, what the step does, input lines, llm lines or None, output lines, kind)
STEPS = [
    ("1 · Doküman okundu", "PyMuPDF / python-docx",
     ["yüklenen PDF veya DOCX", "(arayüzden)"],
     None,
     ["document.raw_text", "sayfa işaretleri [Sayfa N]", "section_map"], "code"),
    ("2 · Sistem modeli", "çıkarım + kanıt denetimi",
     ["document.raw_text", "(uzunsa parçalara bölünür)"],
     ["→ sistem istemi + <document>", "← SystemModel JSON",
      "   bileşen · akış · bölge · kanıt"],
     ["system_model.data", "(sürüm 1)"], "llm"),
    ("— Model onayı", "boru hattı durur, uzman bakar",
     ["sistem modeli + kanıt", "(ekranda)"],
     None,
     ["düzeltilirse sürüm 2", "audit_entry"], "human"),
    ("3 · İlgili bilgi", "hibrit arama, RRF ile birleştirme",
     ["sistem modelindeki öğeler", "kb_chunk (FTS + pgvector)", "bilgi tabanı: 196 kayıt"],
     None,
     ["run_step.output", "öğe → sorgu → kaynaklar"], "code"),
    ("4 · Tehditler", "kural motoru + LLM, sonra birleştirme",
     ["sistem modeli", "3. adımın kaynakları", "kural kataloğu: 59 kural"],
     ["→ model özeti + bilinen başlıklar", "   + <knowledge> + doküman",
      "← tehdit JSON (+ öneri puanı)"],
     ["threat satırları", "evidence · knowledge_sources", "ai_proposed"], "llm"),
    ("5 · Doğrulama", "yedi denetim; eleme yok",
     ["threat satırları", "bilgi tabanı kimlikleri"],
     None,
     ["validation_notes", "validation_status"], "code"),
    ("6 · Risk", "taban + bağlam düzeltmeleri",
     ["kural tabanı veya STRIDE tabanı", "bileşen bağlamı"],
     None,
     ["threat.system_calc", "skor · seviye · kırılım"], "code"),
    ("7 · Önlemler", "katalog eşlemesi, metin LLM'den",
     ["tehdit + bileşen teknolojisi", "önlem kataloğu: 83 önlem"],
     ["→ tehdit + teknoloji", "← bu sisteme göre önlem metni"],
     ["threat.mitigations", "control_mappings"], "llm"),
    ("8 · Uzman incelemesi", "kararı kod kaydeder",
     ["uzmanın kararı + gerekçesi", "(ekrandan)"],
     None,
     ["threat.expert", "review_status", "audit_entry"], "human"),
    ("9 · Rapor", "sayılar koddan, özet metni LLM'den",
     ["tüm tehditler + kararlar", "sistem modeli"],
     ["→ yönetici özeti istemi", "← yalnızca özet paragrafı"],
     ["rapor.pdf · tehditler.xlsx", "analiz.json · otm.json"], "code"),
]

out: list[str] = []


def esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def box(x, y, w, h, fill, stroke, dashed=False):
    dash = ' stroke-dasharray="3 2"' if dashed else ""
    out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="{fill}" '
               f'stroke="{stroke}" stroke-width="1"{dash}/>')


def lines(x, y, items, size=6.3, fill=MUTED, lead=8.4):
    for i, text in enumerate(items):
        out.append(f'<text x="{x}" y="{y + i * lead}" font-size="{size}" '
                   f'fill="{fill}">{esc(text)}</text>')


def arrow_right(x0, x1, y):
    out.append(f'<line x1="{x0}" y1="{y}" x2="{x1 - 5}" y2="{y}" stroke="{SLATE}" stroke-width="1"/>')
    out.append(f'<polygon points="{x1-5},{y-3} {x1-5},{y+3} {x1},{y}" fill="{SLATE}"/>')


for title, x, w in COLS:
    box(x, 0, w, HEAD_H, "#eef2f7", "#cbd5e1")
    out.append(f'<text x="{x + w / 2}" y="{HEAD_H / 2 + 3}" font-size="7" font-weight="bold" '
               f'fill="{INK}" text-anchor="middle">{esc(title)}</text>')

y = HEAD_H + 12
rows: list[tuple[float, float]] = []

for title, doing, inputs, llm, outputs, kind in STEPS:
    rows_needed = max(len(inputs), len(outputs), len(llm or []), 2)
    h = 16 + rows_needed * 8.4
    rows.append((y, h))

    (_, ix, iw), (_, sx, sw), (_, lx, lw), (_, ox, ow) = COLS

    box(ix, y, iw, h, "#f8fafc", "#94a3b8", dashed=True)
    lines(ix + 6, y + 12, inputs)

    fill = {"code": "#ffffff", "llm": "#dbe7f3", "human": "#fff3e3"}[kind]
    box(sx, y, sw, h, fill, "#b45309" if kind == "human" else INK)
    out.append(f'<text x="{sx + 7}" y="{y + 12}" font-size="7.4" font-weight="bold" '
               f'fill="{INK}">{esc(title)}</text>')
    lines(sx + 7, y + 22, [doing], size=6.2)

    if llm:
        box(lx, y, lw, h, "#dbe7f3", INK)
        lines(lx + 6, y + 12, llm, fill="#13456f")
    else:
        box(lx, y, lw, h, "#fcfcfd", "#d7dde5", dashed=True)
        out.append(f'<text x="{lx + lw / 2}" y="{y + h / 2 + 2.5}" font-size="6.4" '
                   f'fill="#9aa4b2" text-anchor="middle">LLM çağrısı yok</text>')

    box(ox, y, ow, h, "#f8fafc", "#94a3b8", dashed=True)
    lines(ox + 6, y + 12, outputs)

    mid = y + h / 2
    arrow_right(ix + iw, sx, mid)
    if llm:
        arrow_right(sx + sw, lx, mid - 4)
        out.append(f'<line x1="{lx}" y1="{mid + 4}" x2="{sx + sw + 5}" y2="{mid + 4}" '
                   f'stroke="{SLATE}" stroke-width="1"/>')
        out.append(f'<polygon points="{sx+sw+5},{mid+1} {sx+sw+5},{mid+7} {sx+sw},{mid+4}" fill="{SLATE}"/>')
        arrow_right(lx + lw, ox, mid)
    else:
        arrow_right(sx + sw, ox, mid)

    y += h + GAP

# The pipeline order, down the step column.
_, sx, sw = COLS[1]
cx = sx + sw / 2
for (y0, h0), (y1, _h) in zip(rows, rows[1:]):
    out.append(f'<line x1="{cx}" y1="{y0 + h0}" x2="{cx}" y2="{y1 - 5}" stroke="{SLATE}" stroke-width="1.2"/>')
    out.append(f'<polygon points="{cx-3.5},{y1-5} {cx+3.5},{y1-5} {cx},{y1}" fill="{SLATE}"/>')

# Every call is recorded; that is what makes replay and the audit possible.
_, lx, lw = COLS[2]
_, ox, ow = COLS[3]
ny = y + 2
box(lx, ny, lw, 20, "#f8fafc", "#94a3b8", dashed=True)
lines(lx + 6, ny + 9, ["Her LLM çağrısı kaydedilir", "istem özeti · süre · token · durum"], size=6)
box(ox, ny, ow, 20, "#f8fafc", "#94a3b8", dashed=True)
lines(ox + 6, ny + 13, ["llm_call satırı → kayıttan tekrar oynatma"], size=6)
arrow_right(lx + lw, ox, ny + 10)

TOTAL = ny + 26
svg = (f'<svg width="{W}" height="{TOTAL}" viewBox="0 0 {W} {TOTAL}" '
       f'xmlns="http://www.w3.org/2000/svg" font-family="DejaVu Sans">\n'
       + "\n".join(out) + "\n</svg>")

page = pathlib.Path(__file__).with_name("mimari.html")
html = page.read_text()
start = html.index("<svg width=")
end = html.index("</svg>") + len("</svg>")
page.write_text(html[:start] + svg + html[end:])
print(f"çizildi: {W}x{TOTAL:.0f}")
