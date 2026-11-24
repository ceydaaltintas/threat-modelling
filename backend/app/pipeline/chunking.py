"""Cutting a document into passages that can be retrieved.

Step 4 used to take the first 18,000 characters of the document and leave
the rest out - silently. In a two page sample that loses nothing; in a
forty page architecture document it loses exactly the parts that come last,
which are usually operations, logging and security.

So the document is cut into overlapping passages, each remembering the page
and section it came from, and step 3 fetches the ones that are about the
component being analysed. The cut is on paragraph boundaries where it can
be: a passage that starts mid-sentence retrieves badly and reads worse when
it ends up in a prompt as evidence.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Long enough to carry a thought, short enough that one component's
# paragraph is not drowned by three others.
TARGET_CHARS = 900
MAX_CHARS = 1_400
# Carried from the previous passage so a sentence split across the cut is
# still findable in one of them.
OVERLAP_CHARS = 150
MIN_CHARS = 120
# How many lines at the top and bottom of a page can be a header/footer.
EDGE_LINES = 2


def repeated_lines(pages: list[str], *, min_share: float = 0.6) -> set[str]:
    """Lines that appear on most pages: headers, footers, page numbers.

    They say nothing about the architecture but they are in every passage,
    so a chunk full of them matches every query and crowds out the real
    answer. Dropped from the passages, not from the document itself, so
    evidence quoting still sees the original text.
    """
    if len(pages) < 2:
        return set()

    # Only the top and bottom of a page can be a header or a footer. A
    # repeated line in the middle is content: "Java, PostgreSQL Uygulama"
    # appears in several rows of a components table, and dropping it would
    # lose a real component.
    counts: dict[str, int] = {}
    for page in pages:
        lines = [ln.strip() for ln in page.splitlines() if ln.strip()]
        edges = {*lines[:EDGE_LINES], *lines[-EDGE_LINES:]}
        for line in edges:
            if len(line) <= 200:
                key = _line_key(line)
                counts[key] = counts.get(key, 0) + 1
    needed = max(2, int(len(pages) * min_share))
    return {key for key, count in counts.items() if count >= needed}


def _line_key(line: str) -> str:
    """A footer differs only by its page number; compare without digits."""
    return re.sub(r"\d+", "#", line).strip()


def strip_lines(text: str, unwanted: set[str]) -> str:
    """Drop header and footer lines, including a half one at the start.

    The overlap that opens a passage can begin in the middle of a header
    line, so the exact match misses it and the fragment survives into the
    prompt. A first line that is part of a header is still a header.
    """
    if not unwanted:
        return text
    kept = [ln for ln in text.splitlines() if _line_key(ln.strip()) not in unwanted]
    while kept:
        head = _line_key(kept[0].strip())
        if len(head) >= 15 and any(head in line for line in unwanted):
            kept.pop(0)
            continue
        break
    return "\n".join(kept).strip()


@dataclass
class Passage:
    text: str
    page: int | None
    section: str | None
    ordinal: int


def _page_of(offset: int, pages: list[tuple[int, int, int]]) -> int | None:
    for page, start, end in pages:
        if start <= offset < end:
            return page
    return None


def _section_of(offset: int, sections: list[tuple[str, int, int]]) -> str | None:
    label = None
    for name, start, end in sections:
        if start <= offset < end:
            label = name
    return label


def split(
    text: str,
    *,
    pages: list[tuple[int, int, int]] | None = None,
    sections: list[tuple[str, int, int]] | None = None,
) -> list[Passage]:
    """Cut ``text`` into passages, keeping page and section with each.

    ``pages`` and ``sections`` are (label, start, end) spans over the same
    text, exactly as the extraction step already records them.
    """
    pages = pages or []
    sections = sections or []
    if not text.strip():
        return []

    # Paragraphs first; a very long paragraph is cut on sentence ends.
    blocks: list[tuple[str, int]] = []
    cursor = 0
    for block in re.split(r"\n\s*\n", text):
        start = text.find(block, cursor)
        if start < 0:
            start = cursor
        cursor = start + len(block)
        stripped = block.strip()
        if stripped:
            blocks.append((stripped, start + block.find(stripped)))

    passages: list[Passage] = []
    buffer = ""
    buffer_start = 0

    def flush() -> None:
        nonlocal buffer, buffer_start
        body = buffer.strip()
        if len(body) >= MIN_CHARS or (body and not passages):
            passages.append(
                Passage(
                    text=body,
                    page=_page_of(buffer_start, pages),
                    section=_section_of(buffer_start, sections),
                    ordinal=len(passages),
                )
            )
        buffer = ""

    for block, start in blocks:
        for piece, piece_start in _fit(block, start):
            if not buffer:
                buffer_start = piece_start
            if len(buffer) + len(piece) + 1 > MAX_CHARS and buffer:
                tail = _tail(buffer)
                flush()
                buffer = tail + "\n" + piece
                buffer_start = piece_start
            else:
                buffer = f"{buffer}\n{piece}".strip() if buffer else piece
            if len(buffer) >= TARGET_CHARS:
                tail = _tail(buffer)
                flush()
                buffer = tail
                buffer_start = piece_start + len(piece) - len(tail)
    flush()

    # The overlap tail on its own is not a passage.
    return [p for p in passages if len(p.text) >= MIN_CHARS or len(passages) == 1]


def _tail(text: str) -> str:
    """The overlap, starting at a word boundary.

    Cutting mid-word retrieves no worse but reads badly when the passage is
    shown as evidence, and "ık platformunun" is not a quote anyone trusts.
    """
    tail = text[-OVERLAP_CHARS:]
    space = tail.find(" ")
    return tail[space + 1 :] if 0 <= space < 40 else tail


def _fit(block: str, start: int) -> list[tuple[str, int]]:
    """A paragraph, or its sentences when it is longer than one passage."""
    if len(block) <= MAX_CHARS:
        return [(block, start)]
    pieces: list[tuple[str, int]] = []
    cursor = 0
    for sentence in re.split(r"(?<=[.!?])\s+", block):
        if not sentence.strip():
            continue
        offset = block.find(sentence, cursor)
        cursor = offset + len(sentence)
        pieces.append((sentence.strip(), start + offset))
    return pieces or [(block, start)]
