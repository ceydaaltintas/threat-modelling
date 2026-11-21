"""The evaluation harness and the expected-findings files."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from app.rules.engine import load_catalog
from scripts.eval import (
    FIXTURE_ATTR,
    grade,
    load_fixture,
    match_finding,
    normalise,
)

EXPECTED_DIR = Path("/samples/expected")

needs_samples = pytest.mark.skipif(
    not EXPECTED_DIR.is_dir(), reason="örnek dosyalar bağlı değil"
)


def expected_files() -> list[dict]:
    return [
        yaml.safe_load(path.read_text(encoding="utf-8"))
        for path in sorted(EXPECTED_DIR.glob("*.yaml"))
    ]


# --- expected findings -------------------------------------------------


@needs_samples
def test_three_documents_are_covered() -> None:
    files = expected_files()
    assert len(files) == 3
    assert {f["sample_key"] for f in files} == {
        "mobil-para-transferi",
        "kredi-basvuru",
        "acik-bankacilik",
    }


@needs_samples
def test_expected_findings_match_the_written_list() -> None:
    """beklenen_bulgular.md lists 37 findings; the YAML must agree."""
    total = sum(len(f["findings"]) for f in expected_files())
    assert total == 37


@needs_samples
def test_every_finding_names_rules_or_keywords() -> None:
    for file in expected_files():
        for finding in file["findings"]:
            assert finding.get("rules") or finding.get("keywords"), finding["id"]
            assert finding["title"].strip()


@needs_samples
def test_every_named_rule_exists_in_the_catalogue() -> None:
    known = {rule.id for rule in load_catalog()}
    missing: dict[str, list[str]] = {}
    for file in expected_files():
        for finding in file["findings"]:
            gaps = [r for r in finding.get("rules", []) if r not in known]
            if gaps:
                missing[finding["id"]] = gaps
    assert not missing, f"Katalogda olmayan kurallar: {missing}"


@needs_samples
def test_finding_ids_are_unique_per_document() -> None:
    for file in expected_files():
        ids = [finding["id"] for finding in file["findings"]]
        assert len(set(ids)) == len(ids)


@needs_samples
def test_each_file_points_at_a_known_fixture() -> None:
    for file in expected_files():
        assert file["fixture"] in FIXTURE_ATTR


# --- fixtures ----------------------------------------------------------


@needs_samples
@pytest.mark.parametrize("name", sorted(FIXTURE_ATTR))
def test_fixture_models_are_valid_and_connected(name: str) -> None:
    model = load_fixture(name)
    assert len(model.components) >= 10
    assert model.data_flows
    # Every flow endpoint must exist, or the rule engine would skip it.
    assert model.dangling_flows() == []


@needs_samples
@pytest.mark.parametrize("name", sorted(FIXTURE_ATTR))
def test_fixture_components_carry_evidence(name: str) -> None:
    model = load_fixture(name)
    assert all(component.evidence for component in model.components)


# --- matching ----------------------------------------------------------


def test_finding_is_caught_by_a_rule() -> None:
    finding = {"id": "x", "title": "t", "rules": ["R-API-BOLA"], "keywords": []}
    threats = [{"rule_id": "R-API-BOLA", "title": "BOLA", "description": ""}]
    result = match_finding(finding, threats)
    assert result["caught"] is True
    assert result["how"] == "rule"


def test_finding_is_caught_by_a_keyword_when_no_rule_matched() -> None:
    finding = {
        "id": "x",
        "title": "t",
        "rules": ["R-YOK"],
        "keywords": ["sertifika sabitleme"],
    }
    threats = [
        {
            "rule_id": None,
            "title": "Mobil uygulamada sertifika sabitleme yok",
            "description": "",
        }
    ]
    result = match_finding(finding, threats)
    assert result["caught"] is True
    assert result["how"] == "keyword"


def test_unrelated_threats_do_not_count() -> None:
    finding = {"id": "x", "title": "t", "rules": ["R-YOK"], "keywords": ["otp"]}
    threats = [{"rule_id": "R-BASKA", "title": "Yedek şifrelemesi", "description": ""}]
    assert match_finding(finding, threats)["caught"] is False


def test_keyword_matching_ignores_case_and_accents() -> None:
    finding = {"id": "x", "title": "t", "rules": [], "keywords": ["SIM değiştirme"]}
    threats = [{"rule_id": None, "title": "sim degistirme riski", "description": ""}]
    assert match_finding(finding, threats)["caught"] is True


def test_normalise_folds_turkish_characters() -> None:
    assert normalise("ŞİFRELEME") == normalise("sifreleme")


def test_grade_reports_recall_and_counts() -> None:
    expected = {
        "document": "d.pdf",
        "sample_key": "k",
        "findings": [
            {"id": "1", "title": "a", "rules": ["R-A"], "keywords": []},
            {"id": "2", "title": "b", "rules": ["R-B"], "keywords": []},
        ],
    }
    threats = [
        {
            "rule_id": "R-A",
            "title": "a",
            "description": "",
            "evidence": [{"quote": "x"}],
            "validation_notes": [],
        },
        {
            "rule_id": "R-C",
            "title": "c",
            "description": "",
            "evidence": [],
            "validation_notes": [
                {"code": "unknown_knowledge_id", "detail": "CWE-99999"}
            ],
        },
    ]
    report = grade(expected, threats)
    assert report["caught"] == 1
    assert report["expected"] == 2
    assert report["recall"] == 0.5
    assert report["assumptions"] == 1
    assert report["unknown_identifiers"] == 1


# --- rule coverage gate ------------------------------------------------


@needs_samples
def test_rule_catalogue_catches_every_expected_finding() -> None:
    """The quality gate: 37/37 with a correct system model and no LLM.

    This measures the rule catalogue, not the extraction and not security
    effectiveness - the system models here are hand built.
    """
    from app.rules.engine import evaluate

    misses: list[str] = []
    for file in expected_files():
        model = load_fixture(file["fixture"])
        threats = [
            {
                "rule_id": threat.rule_id,
                "title": threat.title,
                "description": threat.description,
                "evidence": threat.evidence,
                "validation_notes": [],
            }
            for threat in evaluate(model, "")
        ]
        for finding in file["findings"]:
            if not match_finding(finding, threats)["caught"]:
                misses.append(f"{file['sample_key']} {finding['id']}")
    assert not misses, f"Yakalanamayan beklenen bulgular: {misses}"
