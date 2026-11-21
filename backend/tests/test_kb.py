"""Knowledge base content and the parts of search that need no database."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.kb.loader import KB_DIR, read_entries, searchable_text
from app.kb.search import _to_tsquery, identifiers_in
from app.rules.engine import load_catalog

needs_kb = pytest.mark.skipif(
    not any(KB_DIR.glob("*.jsonl")), reason="bilgi tabanı dosyaları yok"
)


# --- identifier detection -------------------------------------------


def test_identifier_is_detected_in_a_sentence() -> None:
    assert identifiers_in("CWE-89 ile ilgili tehditler") == ["CWE-89"]


def test_several_identifier_styles_are_detected() -> None:
    found = identifiers_in("API1:2023 ve T1566 ve A01:2021 ve ASVS-V4")
    assert {"API1:2023", "T1566", "A01:2021", "ASVS-V4"} <= set(found)


def test_plain_words_are_not_identifiers() -> None:
    assert identifiers_in("şifreleme eksikliği") == []


def test_tsquery_builder_drops_punctuation() -> None:
    assert _to_tsquery("loglara IBAN yazılıyor!") == "loglara | iban | yazılıyor"


def test_tsquery_keeps_identifiers_intact() -> None:
    assert "cwe-89" in _to_tsquery("CWE-89 nedir")


def test_tsquery_of_empty_input_is_empty() -> None:
    assert _to_tsquery("   ") == ""


# --- curated content ------------------------------------------------


@needs_kb
def test_knowledge_base_is_large_enough() -> None:
    assert len(read_entries()) >= 150


@needs_kb
def test_every_entry_has_identifier_title_text_and_licence() -> None:
    for item in read_entries():
        assert item["identifier"].strip()
        assert item["title"].strip()
        assert len(item["text"]) > 40, item["identifier"]
        assert item["license"].strip(), item["identifier"]


@needs_kb
def test_identifiers_are_unique_within_a_source() -> None:
    seen = set()
    for item in read_entries():
        key = (item["source"], item["identifier"], item.get("lang", "tr"))
        assert key not in seen, key
        seen.add(key)


@needs_kb
def test_copyrighted_standards_carry_only_a_summary() -> None:
    """ISO entries must be short summaries, flagged for verification."""
    iso = [item for item in read_entries() if item["source"] == "iso27001"]
    assert iso
    for item in iso:
        assert item.get("verification") == "needed", item["identifier"]
        # A summary, not the clause text.
        assert len(item["text"]) < 400, item["identifier"]


@needs_kb
def test_turkish_regulation_is_reference_level_only() -> None:
    tr = [item for item in read_entries() if item["source"] == "tr_regulation"]
    assert tr
    for item in tr:
        assert item.get("verification") == "needed"
        assert item["url"]


@needs_kb
def test_entries_carry_an_embedding_of_the_right_size() -> None:
    from app.models.entities import EMBEDDING_DIM

    entries = read_entries()
    with_vector = [item for item in entries if item.get("embedding")]
    assert with_vector, "gömme vektörü olan kayıt yok"
    assert len(with_vector) == len(entries)
    assert all(len(item["embedding"]) == EMBEDDING_DIM for item in with_vector)


@needs_kb
def test_searchable_text_includes_identifier_and_tags() -> None:
    item = read_entries()[0]
    text = searchable_text(item)
    assert item["identifier"] in text
    assert item["title"] in text


@needs_kb
def test_every_rule_source_exists_in_the_knowledge_base() -> None:
    """A rule may not cite an identifier the knowledge base does not have."""
    available = {item["identifier"].upper() for item in read_entries()}
    missing: dict[str, list[str]] = {}
    for rule in load_catalog():
        gaps = [kid for kid in rule.knowledge_ids if kid.upper() not in available]
        if gaps:
            missing[rule.id] = gaps
    assert not missing, f"Bilgi tabanında olmayan kaynak kimlikleri: {missing}"


@needs_kb
def test_jsonl_files_are_valid_json_per_line() -> None:
    for path in sorted(Path(KB_DIR).glob("*.jsonl")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip():
                json.loads(line)  # raises on malformed content
