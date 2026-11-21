"""The mitigation catalogue and its control framework mappings."""

from __future__ import annotations

import re

from app.controls import catalog
from app.kb.loader import read_entries
from app.rules.engine import load_catalog as load_rules


def test_catalogue_loads_and_ids_are_unique() -> None:
    mitigations = catalog.load_mitigations()
    assert len(mitigations) >= 50
    assert all(re.fullmatch(r"M-[A-Z0-9-]+", mid) for mid in mitigations)


def test_every_mitigation_has_a_title_and_actionable_text() -> None:
    for mitigation in catalog.load_mitigations().values():
        assert mitigation.title.strip()
        assert len(mitigation.text) > 40, mitigation.id
        # Wrapped text must not have lost its spaces.
        assert "  " not in mitigation.text


def test_every_mitigation_named_by_a_rule_exists() -> None:
    defined = set(catalog.load_mitigations())
    used = {mid for rule in load_rules() for mid in rule.mitigations}
    assert not used - defined, f"Tanımsız önlem: {sorted(used - defined)}"


def test_no_orphan_mitigations() -> None:
    """Every catalogue entry is reachable from a rule or a STRIDE fallback."""
    from app.pipeline.step7_mitigations import STRIDE_MITIGATIONS

    used = {mid for rule in load_rules() for mid in rule.mitigations}
    used |= {mid for ids in STRIDE_MITIGATIONS.values() for mid in ids}
    orphans = set(catalog.load_mitigations()) - used
    assert not orphans, f"Hiçbir kuralın kullanmadığı önlem: {sorted(orphans)}"


def test_control_identifiers_exist_in_the_knowledge_base() -> None:
    available = {entry["identifier"] for entry in read_entries()}
    used = {
        control.id
        for mitigation in catalog.load_mitigations().values()
        for control in mitigation.controls
    }
    assert not used - available, f"Bilgi tabanında yok: {sorted(used - available)}"


def test_iso_mappings_are_marked_for_verification() -> None:
    """ISO clause numbers are never presented as confirmed."""
    for mitigation in catalog.load_mitigations().values():
        for control in mitigation.controls:
            if control.framework == "ISO 27001:2022":
                assert control.verification == "needed", mitigation.id


def test_control_mappings_are_deduplicated_and_sorted() -> None:
    mappings = catalog.control_mappings(["M-AUTHZ-OBJECT", "M-AUTHZ-FUNCTION"])
    keys = [(m["framework"], m["id"]) for m in mappings]
    assert len(keys) == len(set(keys))
    assert keys == sorted(keys)


def test_mapping_records_which_mitigation_it_came_from() -> None:
    mappings = catalog.control_mappings(["M-RATE-LIMIT"])
    assert mappings
    assert all(m["via"] == "M-RATE-LIMIT" for m in mappings)


def test_unknown_mitigation_id_is_ignored_rather_than_crashing() -> None:
    assert catalog.control_mappings(["M-YOK-BOYLE-BIR-SEY"]) == []
