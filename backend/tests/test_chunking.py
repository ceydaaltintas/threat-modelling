"""Cutting a document into retrievable passages."""

from __future__ import annotations

from app.pipeline.chunking import MAX_CHARS, MIN_CHARS, split


def test_a_short_document_is_one_passage() -> None:
    passages = split("Transfer Servisi limitleri kontrol eder.")

    assert len(passages) == 1
    assert passages[0].page is None


def test_a_long_document_is_cut_into_several() -> None:
    body = "\n\n".join(f"Paragraf {i}. " + "metin " * 60 for i in range(12))

    passages = split(body)

    assert len(passages) > 3
    assert all(len(p.text) <= MAX_CHARS for p in passages)
    assert all(len(p.text) >= MIN_CHARS for p in passages)


def test_each_passage_remembers_its_page_and_section() -> None:
    body = "A" * 500 + "\n\n" + "B" * 500 + "\n\n" + "C" * 500
    pages = [(1, 0, 600), (2, 600, len(body))]
    sections = [("1 Giriş", 0, 600), ("2 Bileşenler", 600, len(body))]

    passages = split(body, pages=pages, sections=sections)

    assert passages[0].page == 1
    assert passages[0].section == "1 Giriş"
    assert passages[-1].page == 2
    assert passages[-1].section == "2 Bileşenler"


def test_passages_overlap_so_a_split_sentence_is_still_findable() -> None:
    body = "\n\n".join("cümle " * 40 for _ in range(6))

    passages = split(body)

    assert len(passages) > 1
    # The tail of one passage opens the next.
    assert passages[1].text.startswith("cümle")


def test_an_empty_document_gives_nothing() -> None:
    assert split("   \n  ") == []


# --- What of the document reaches the prompt ---------------------------


def test_a_document_that_fits_is_sent_whole() -> None:
    from app.pipeline.step4_threats import _document_blocks

    text, retrieved = _document_blocks({}, "kısa doküman")

    assert text == "kısa doküman"
    assert retrieved is False


def test_a_long_document_is_replaced_by_retrieved_passages() -> None:
    """The old behaviour cut at 18.000 characters and dropped the rest."""
    from app.pipeline.step4_threats import MAX_DOCUMENT_CHARS, _document_blocks

    long_text = "x" * (MAX_DOCUMENT_CHARS + 1)
    retrieved = {
        "elements": [
            {
                "passages": [
                    {
                        "text": "Transfer Servisi limitleri kontrol eder.",
                        "page": 7,
                        "section": "5 Güvenlik",
                    }
                ]
            }
        ]
    }

    text, used_retrieval = _document_blocks(retrieved, long_text)

    assert used_retrieval is True
    assert "Transfer Servisi limitleri" in text
    assert "sayfa 7" in text and "5 Güvenlik" in text
    assert "x" not in text


def test_the_same_passage_is_not_repeated() -> None:
    from app.pipeline.step4_threats import MAX_DOCUMENT_CHARS, _document_blocks

    passage = {"text": "Aynı paragraf", "page": 1, "section": None}
    retrieved = {"elements": [{"passages": [passage]}, {"passages": [passage]}]}

    text, _ = _document_blocks(retrieved, "y" * (MAX_DOCUMENT_CHARS + 1))

    assert text.count("Aynı paragraf") == 1


def test_without_passages_the_old_cut_is_used_rather_than_nothing() -> None:
    from app.pipeline.step4_threats import MAX_DOCUMENT_CHARS, _document_blocks

    text, used_retrieval = _document_blocks({}, "z" * (MAX_DOCUMENT_CHARS + 50))

    assert used_retrieval is False
    assert len(text) == MAX_DOCUMENT_CHARS


# --- Headers and footers ----------------------------------------------


def test_a_repeated_header_is_dropped() -> None:
    from app.pipeline.chunking import repeated_lines

    pages = [
        "Örnek Banka A.Ş. | Mimari\nTransfer Servisi limit kontrolü yapar.\n"
        "Çekirdek bankacılığa kuyrukla iletir.\nAlt bilgi",
        "Örnek Banka A.Ş. | Mimari\nLimit Servisi sayaçları Redis'te tutar.\n"
        "Günlük limitler müşteri bazlıdır.\nAlt bilgi",
        "Örnek Banka A.Ş. | Mimari\nBildirim Servisi SMS gönderir.\n"
        "Push bildirimi de destekler.\nAlt bilgi",
    ]

    assert repeated_lines(pages) == {"Örnek Banka A.Ş. | Mimari", "Alt bilgi"}


def test_a_footer_with_a_page_number_is_still_one_footer() -> None:
    """Every page's footer differs by its number; it is the same footer."""
    from app.pipeline.chunking import repeated_lines, strip_lines

    pages = [
        "Giriş metni\nDahili belge · Sayfa 1",
        "İkinci sayfa metni\nDahili belge · Sayfa 2",
        "Üçüncü sayfa metni\nDahili belge · Sayfa 3",
    ]

    found = repeated_lines(pages)

    assert found == {"Dahili belge · Sayfa #"}
    assert strip_lines("Dahili belge · Sayfa 2\nGerçek cümle", found) == "Gerçek cümle"


def test_a_repeated_line_in_the_body_is_content_not_a_header() -> None:
    """A components table repeats values; dropping them loses components."""
    from app.pipeline.chunking import repeated_lines

    pages = [
        "Başlık A\nbir\niki\nJava, PostgreSQL Uygulama\nüç\ndört\nAlt bilgi",
        "Başlık B\nbeş\naltı\nJava, PostgreSQL Uygulama\nyedi\nsekiz\nAlt bilgi",
    ]

    found = repeated_lines(pages)

    assert "Java, PostgreSQL Uygulama" not in found
    assert "Alt bilgi" in found


def test_stripping_leaves_the_rest_alone() -> None:
    from app.pipeline.chunking import strip_lines

    text = "Üst bilgi\nGerçek cümle\nÜst bilgi\nİkinci cümle"

    assert strip_lines(text, {"Üst bilgi"}) == "Gerçek cümle\nİkinci cümle"
