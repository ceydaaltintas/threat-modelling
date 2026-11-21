"""Text extraction and the page/section index."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.pipeline import extract

SAMPLES = Path("/samples/documents")
PDF = SAMPLES / "01_mobil_bankacilik_para_transferi.pdf"

needs_samples = pytest.mark.skipif(
    not PDF.is_file(), reason="örnek dokümanlar bağlı değil"
)


def test_detect_doc_type_covers_the_accepted_formats() -> None:
    assert extract.detect_doc_type("a.pdf") == "pdf"
    assert extract.detect_doc_type("a.DOCX") == "docx"
    assert extract.detect_doc_type("notlar.md") == "text"
    assert extract.detect_doc_type("diagram.PNG") == "image"


def test_detect_doc_type_rejects_other_formats_in_turkish() -> None:
    with pytest.raises(extract.UnsupportedDocument) as info:
        extract.detect_doc_type("zararli.exe")
    assert "desteklenmeyen" in str(info.value).lower()


def test_text_file_is_indexed_by_section(tmp_path: Path) -> None:
    path = tmp_path / "mimari.md"
    path.write_text(
        "1. Amaç\nBu bölüm amacı anlatır.\n"
        "2. Bileşenler\nServis A ve Servis B vardır.\n"
        "2.1 Servis A\nSpring Boot ile yazılmıştır.\n",
        encoding="utf-8",
    )

    result = extract.extract(path, "text")

    assert result.page_count == 1
    assert [s.number for s in result.sections] == ["1", "2", "2.1"]
    assert result.sections[0].title == "Amaç"


def test_numbered_sentences_are_not_treated_as_headings(tmp_path: Path) -> None:
    path = tmp_path / "akis.txt"
    path.write_text(
        "4. Ana akış\n"
        "3 Transfer Servisi, istek gövdesindeki hesap numarasının müşteriye "
        "ait olup olmadığını kontrol etmez.\n"
        "5. Güvenlik\n",
        encoding="utf-8",
    )

    result = extract.extract(path, "text")

    assert [s.number for s in result.sections] == ["4", "5"]


def test_section_ranges_do_not_overlap(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_text("1. Bir\nmetin\n2. İki\nmetin\n3. Üç\nson\n", encoding="utf-8")

    result = extract.extract(path, "text")

    for first, second in zip(result.sections, result.sections[1:]):
        assert first.end == second.start
    assert result.sections[-1].end >= result.sections[-1].start


@needs_samples
def test_sample_pdf_yields_text_pages_and_sections() -> None:
    result = extract.extract(PDF, "pdf")

    assert result.page_count == 2
    assert result.char_count > 3000
    assert result.needs_vision is False
    numbers = [s.number for s in result.sections]
    # The document's own numbered sections, no list-item noise.
    assert {"1", "2", "3", "4", "5"} <= set(numbers)


@needs_samples
def test_section_map_maps_offsets_back_to_pages() -> None:
    result = extract.extract(PDF, "pdf")
    entries = result.to_section_map()

    pages = [e for e in entries if e["type"] == "page"]
    assert [p["page"] for p in pages] == [1, 2]
    text = result.full_text
    for page in pages:
        assert text[page["start"] : page["end"]] == result.pages[page["page"] - 1].text
