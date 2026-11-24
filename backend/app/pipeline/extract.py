"""Step 1: turn uploaded files into text with a page and section index.

Supported inputs: PDF (pypdfium2), DOCX (python-docx), Markdown/plain text and
images. A PDF whose pages carry almost no text is treated as scanned: the
pages are rendered to PNG so the LLM can read them visually. OCR is only a
fallback and is off by default (``OCR_ENABLED``).

Nothing here interprets the content - it only produces text plus the index
that lets the UI jump to the place a quote came from.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from app.pipeline import diagrams

# A page with fewer characters than this is treated as having no text layer.
MIN_CHARS_PER_PAGE = 60
# Rendering scale for scanned pages handed to the vision model.
PAGE_RENDER_SCALE = 2.0

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
TEXT_SUFFIXES = {".md", ".markdown", ".txt", ".text"}

# Headings are short; numbered sentences inside a section are not. Anything
# longer than this is treated as body text, not a heading.
MAX_HEADING_TITLE = 60
MAX_HEADING_LINE = 80

# "4. Amaç ve kapsam", "4.1 Yetkilendirme", "Bölüm 5" ...
_HEADING_PATTERNS = (
    re.compile(r"^\s*(?P<no>[1-9]\d*(?:\.\d+)*)[.)]?\s+(?P<title>\S.*)$"),
    re.compile(r"^\s*(?P<no>Bölüm\s+\d+(?:\.\d+)*)[.:)]?\s*(?P<title>\S.*)$", re.I),
)
# Lines that look like a heading number but are really table or list noise:
# a sentence (ends in punctuation), a decimal number, or a trailing comma.
_HEADING_REJECT = re.compile(r"[.!?,;:]$|^\d+[.,]\d+$")


@dataclass
class Section:
    """One numbered section of the document."""

    number: str
    title: str
    page: int
    # Character offsets into the document's full text.
    start: int
    end: int

    @property
    def label(self) -> str:
        return f"{self.number} {self.title}".strip()


@dataclass
class PageText:
    page: int
    text: str
    start: int
    end: int


@dataclass
class ExtractionResult:
    pages: list[PageText] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    # Page images handed to the vision model when there is no text layer.
    images: list[bytes] = field(default_factory=list)
    note: str | None = None

    @property
    def full_text(self) -> str:
        return "\n".join(page.text for page in self.pages)

    @property
    def page_count(self) -> int:
        return len(self.pages)

    @property
    def char_count(self) -> int:
        return sum(len(page.text) for page in self.pages)

    @property
    def needs_vision(self) -> bool:
        return bool(self.images) and self.char_count < MIN_CHARS_PER_PAGE

    def to_section_map(self) -> list[dict]:
        """JSON shape stored on ``document.section_map`` and used by the UI."""
        return [
            {
                "type": "page",
                "page": page.page,
                "start": page.start,
                "end": page.end,
            }
            for page in self.pages
        ] + [
            {
                "type": "section",
                "number": section.number,
                "title": section.title,
                "label": section.label,
                "page": section.page,
                "start": section.start,
                "end": section.end,
            }
            for section in self.sections
        ]


class UnsupportedDocument(Exception):
    """Raised with a Turkish, actionable message for the UI."""


def detect_doc_type(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix == ".docx":
        return "docx"
    if suffix in DIAGRAM_SUFFIXES:
        return "diagram"
    if suffix in IMAGE_SUFFIXES:
        return "image"
    if suffix in TEXT_SUFFIXES:
        return "text"
    raise UnsupportedDocument(
        f"'{filename}' desteklenmeyen bir dosya türü. "
        "PDF, DOCX, DRAWIO, XML, VSDX, MD, TXT, PNG veya JPG yükleyin."
    )


def extract(path: Path, doc_type: str) -> ExtractionResult:
    if doc_type == "pdf":
        return _extract_pdf(path)
    if doc_type == "docx":
        return _extract_docx(path)
    if doc_type == "text":
        return _extract_text(path)
    if doc_type == "image":
        return _extract_image(path)
    if doc_type == "diagram":
        return _extract_diagram(path)
    raise UnsupportedDocument(f"Bilinmeyen doküman türü: {doc_type}")


def _assemble(raw_pages: list[str]) -> tuple[list[PageText], list[Section]]:
    pages: list[PageText] = []
    offset = 0
    for index, text in enumerate(raw_pages, start=1):
        pages.append(
            PageText(page=index, text=text, start=offset, end=offset + len(text))
        )
        # +1 for the newline join in ``full_text``
        offset += len(text) + 1
    return pages, _find_sections(pages)


def _find_sections(pages: list[PageText]) -> list[Section]:
    found: list[Section] = []
    for page in pages:
        cursor = page.start
        for line in page.text.split("\n"):
            stripped = line.strip()
            if 3 <= len(stripped) <= MAX_HEADING_LINE and not _HEADING_REJECT.search(
                stripped
            ):
                for pattern in _HEADING_PATTERNS:
                    match = pattern.match(stripped)
                    if match and len(match.group("title")) <= MAX_HEADING_TITLE:
                        found.append(
                            Section(
                                number=match.group("no").strip(),
                                title=match.group("title").strip(),
                                page=page.page,
                                start=cursor,
                                end=cursor,  # fixed up below
                            )
                        )
                        break
            cursor += len(line) + 1

    # A section runs until the next one starts (or the end of the document).
    total = pages[-1].end if pages else 0
    for index, section in enumerate(found):
        section.end = found[index + 1].start if index + 1 < len(found) else total
    return found


def _extract_pdf(path: Path) -> ExtractionResult:
    # pypdfium2 (Apache-2.0 / BSD-3-Clause) rather than PyMuPDF (AGPL-3.0):
    # the AGPL would reach the whole project once it is distributed.
    import io

    import pypdfium2 as pdfium

    raw_pages: list[str] = []
    images: list[bytes] = []
    document = pdfium.PdfDocument(str(path))
    try:
        for page in document:
            textpage = page.get_textpage()
            try:
                # get_text_bounded: whole page, and no deprecation warning.
                # PDFium returns CRLF; the rest of the pipeline counts
                # offsets in this text, so normalise the line endings once.
                text = (textpage.get_text_bounded() or "").replace("\r\n", "\n")
                text = text.replace("\r", "\n").strip()
            finally:
                textpage.close()
            raw_pages.append(text)
            if len(text) < MIN_CHARS_PER_PAGE:
                # No usable text layer: hand the rendered page to the model.
                bitmap = page.render(scale=PAGE_RENDER_SCALE)
                buffer = io.BytesIO()
                bitmap.to_pil().save(buffer, format="PNG")
                images.append(buffer.getvalue())
            page.close()
    finally:
        document.close()

    # A diagram in a PDF is reported, never guessed at: see
    # diagrams.detect_pdf_diagrams for why reading it was dropped.
    drawn = diagrams.detect_pdf_diagrams(path)
    if drawn:
        raw_pages.append("\n\n".join(d.as_text() for d in drawn))

    pages, sections = _assemble(raw_pages)
    result = ExtractionResult(pages=pages, sections=sections, images=images)
    if images and result.char_count < MIN_CHARS_PER_PAGE:
        result.note = (
            f"{len(images)} sayfada metin katmanı bulunamadı; sayfalar görsel "
            "olarak okunacak."
        )
    elif images:
        result.note = (
            f"{len(images)} sayfa metin katmanı içermiyor; bu sayfalar görsel "
            "olarak okunacak."
        )
    diagram_note = _diagram_note(drawn)
    if diagram_note:
        result.note = f"{result.note} {diagram_note}".strip() if result.note else diagram_note
    return result


def _extract_docx(path: Path) -> ExtractionResult:
    import docx

    document = docx.Document(str(path))
    parts: list[str] = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            if any(cells):
                parts.append(" | ".join(cells))

    # Diagrams were invisible before: python-docx reads paragraphs and
    # tables only. Anything the file carries as structure - Word shapes, a
    # pasted draw.io picture, an embedded Visio object - becomes text here
    # and is read by the same step that reads the prose.
    found = diagrams.parse_docx(path)
    for diagram in found:
        parts.append("")
        parts.append(diagram.as_text())

    # DOCX has no fixed pagination; the whole document is one "page".
    pages, sections = _assemble(["\n".join(parts).strip()])
    note = "DOCX dosyalarında sayfa bilgisi yoktur; bölüm başlıkları kullanılır."
    diagram_note = _diagram_note(found)
    return ExtractionResult(
        pages=pages,
        sections=sections,
        note=f"{note} {diagram_note}".strip() if diagram_note else note,
    )


DIAGRAM_SUFFIXES = {".drawio", ".vsdx", ".xml"}


def _diagram_note(found: list["diagrams.Diagram"]) -> str | None:
    """One line about what the diagrams gave us, for the document panel."""
    if not found:
        return None
    readable = [d for d in found if d.nodes or d.edges]
    unreadable = [d for d in found if d.unreadable and not (d.nodes or d.edges)]
    parts = []
    if readable:
        boxes = sum(len(d.nodes) for d in readable)
        arrows = sum(len(d.edges) for d in readable)
        parts.append(
            f"{len(readable)} şema okundu ({boxes} kutu, {arrows} akış)."
        )
    if unreadable:
        parts.append(
            f"{len(unreadable)} görsel kutu/ok bilgisi taşımıyor; şemadaki "
            "bileşenleri model onayı adımında ekleyebilirsiniz."
        )
    return " ".join(parts)


def _extract_diagram(path: Path) -> ExtractionResult:
    """A diagram uploaded on its own (.drawio / .vsdx)."""
    found = diagrams.parse_file(path)
    if not found:
        raise UnsupportedDocument(
            f"'{path.name}' içinden kutu ve ok okunamadı. draw.io dosyası "
            "ise 'Sıkıştırılmamış XML' olarak kaydedip tekrar deneyin; "
            "Visio ise .vsdx olarak dışa aktarın."
        )
    body = "\n\n".join(diagram.as_text() for diagram in found)
    pages, sections = _assemble([body])
    return ExtractionResult(pages=pages, sections=sections, note=_diagram_note(found))


def _extract_text(path: Path) -> ExtractionResult:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    pages, sections = _assemble([text])
    return ExtractionResult(pages=pages, sections=sections)


def _extract_image(path: Path) -> ExtractionResult:
    data = path.read_bytes()
    pages, sections = _assemble([""])
    return ExtractionResult(
        pages=pages,
        sections=sections,
        images=[data],
        note="Görsel dosya; içerik LLM'in görsel okuma yeteneğiyle çözümlenecek.",
    )
