"""The rule catalogue and its engine."""

from __future__ import annotations

import pytest

from app.rules.engine import evaluate, load_catalog, normalise
from app.rules.schema import Rule
from app.schemas.system_model import SystemModel
from tests.fixtures.mobile_transfer_model import MOBILE_TRANSFER_MODEL


@pytest.fixture(scope="module")
def model() -> SystemModel:
    return SystemModel.model_validate(MOBILE_TRANSFER_MODEL)


@pytest.fixture(scope="module")
def threats(model: SystemModel):
    return evaluate(model, "")


def test_catalogue_meets_the_minimum_size() -> None:
    # The catalogue is expected to hold at least 40 rules.
    assert len(load_catalog()) >= 40


def test_rule_ids_are_unique() -> None:
    ids = [rule.id for rule in load_catalog()]
    assert len(set(ids)) == len(ids)


def test_every_rule_cites_at_least_one_source() -> None:
    for rule in load_catalog():
        assert rule.knowledge_ids, f"{rule.id} kaynaksız"


def test_every_rule_has_a_scenario_and_mitigations() -> None:
    for rule in load_catalog():
        assert rule.scenario.strip(), f"{rule.id} senaryosuz"
        assert rule.mitigations, f"{rule.id} önlemsiz"


def test_banking_areas_are_covered() -> None:
    areas = {rule.area for rule in load_catalog()}
    # The banking areas the catalogue must cover.
    assert {"api", "kimlik", "odeme", "veri", "mobil", "altyapi", "ucuncu-taraf",
            "log", "yapay-zeka"} <= areas


def test_normalise_folds_turkish_accents() -> None:
    assert normalise("ŞİFRELENMEMİŞ") == normalise("sifrelenmemis")
    assert normalise("Güven  Bölgesi") == "guven bolgesi"


# --- matching behaviour ---------------------------------------------


def test_unencrypted_flow_raises_disclosure_and_tampering(threats) -> None:
    fired = {t.rule_id for t in threats if t.flow_ref == "f-transfer-limit"}
    assert {"R-FLOW-PLAINTEXT", "R-FLOW-PLAINTEXT-TAMPER"} <= fired


def test_unauthenticated_flow_is_flagged(threats) -> None:
    fired = {t.rule_id for t in threats if t.flow_ref == "f-transfer-fraud"}
    assert "R-FLOW-UNAUTHENTICATED" in fired


def test_unknown_encryption_is_reported_as_an_open_question(threats) -> None:
    fired = {t.rule_id for t in threats if t.flow_ref == "f-transfer-db"}
    assert "R-FLOW-UNKNOWN-ENCRYPTION" in fired
    # ... and not as a confirmed plaintext finding.
    assert "R-FLOW-PLAINTEXT" not in fired


def test_mobile_rules_only_hit_the_mobile_app(threats) -> None:
    for threat in threats:
        if threat.rule_id.startswith("R-MOB-NO-"):
            assert threat.component_ref == "mobil-uygulama"


def test_gateway_is_not_accused_of_object_level_authorisation(threats) -> None:
    bola = {t.component_ref for t in threats if t.rule_id == "R-API-BOLA"}
    assert "api-gecidi" not in bola
    assert "transfer-servisi" in bola


def test_llm_rules_do_not_fire_without_an_ai_component(threats) -> None:
    assert not [t for t in threats if t.rule_id.startswith("R-LLM-")]


def test_threats_inherit_the_evidence_of_their_element(threats) -> None:
    with_evidence = [t for t in threats if t.component_ref == "mobil-uygulama"]
    assert with_evidence
    assert all(t.evidence for t in with_evidence)


def test_element_without_evidence_produces_assumption_threats(threats) -> None:
    # f-transfer-db carries no evidence quote in the fixture.
    flow_threats = [t for t in threats if t.flow_ref == "f-transfer-db"]
    assert flow_threats
    assert all(not t.evidence for t in flow_threats)


def test_context_flags_mark_internet_facing_components(threats) -> None:
    mobile = next(t for t in threats if t.component_ref == "mobil-uygulama")
    assert mobile.context.internet_facing is True
    internal = next(t for t in threats if t.component_ref == "limit-servisi")
    assert internal.context.internet_facing is False


def test_control_keyword_in_document_is_detected(model: SystemModel) -> None:
    without = evaluate(model, "")
    with_control = evaluate(
        model, "Mobil uygulamada sertifika sabitleme uygulanmaktadır."
    )
    pinning_before = next(t for t in without if t.rule_id == "R-MOB-NO-PINNING")
    pinning_after = next(t for t in with_control if t.rule_id == "R-MOB-NO-PINNING")
    assert pinning_before.context.control_evidence is None
    assert pinning_after.context.control_evidence == "sertifika sabitleme"


def test_system_level_rule_fires_once(threats) -> None:
    monitoring = [t for t in threats if t.rule_id == "R-INFRA-NO-MONITORING"]
    assert len(monitoring) == 1
    assert monitoring[0].component_ref is None


def test_empty_model_produces_no_component_threats() -> None:
    assert evaluate(SystemModel(), "") == []


# --- coverage against the expert's expected findings -----------------

# samples/expected/beklenen_bulgular.md, document 1. Each expected finding
# maps to the rule(s) that should catch it. This is a quality gate on the
# catalogue, not a measure of security effectiveness.
EXPECTED_DOC1 = {
    "1-1 BOLA / hesap sahipliği": ["R-API-BOLA"],
    "1-2 fail-open dolandırıcılık kontrolü": ["R-PAY-FAIL-OPEN"],
    "1-3 şifresiz iç ağ trafiği": ["R-FLOW-PLAINTEXT", "R-FLOW-PLAINTEXT-TAMPER"],
    "1-4 limit sayacında yarış durumu": ["R-PAY-RACE-LIMIT"],
    "1-5 tekrar önleme yok": ["R-PAY-NO-IDEMPOTENCY"],
    "1-6 OTP deneme sınırı / SMS kanalı": [
        "R-AUTH-OTP-BRUTEFORCE",
        "R-AUTH-SMS-OTP-CHANNEL",
    ],
    "1-7 loglarda hassas veri": ["R-DATA-LOG-SENSITIVE"],
    "1-8 ortak yönetici hesabı, MFA yok, kayıt yok": [
        "R-AUTH-SHARED-ACCOUNT",
        "R-AUTH-NO-MFA-ADMIN",
        "R-DATA-NO-AUDIT-TRAIL",
    ],
    "1-9 mobil: pinning, root tespiti, karartma": [
        "R-MOB-NO-PINNING",
        "R-MOB-NO-ROOT-DETECTION",
    ],
    "1-10 uzun ömürlü token": ["R-AUTH-LONG-LIVED-TOKEN"],
    "1-11 SMS içeriği": ["R-MOB-NOTIFICATION-CONTENT"],
    "1-12 yedek şifrelemesi": ["R-DATA-BACKUP-ENCRYPTION"],
}


def test_rule_catalogue_covers_the_expected_findings(threats) -> None:
    fired = {threat.rule_id for threat in threats}
    missing = {
        finding: rules
        for finding, rules in EXPECTED_DOC1.items()
        if not set(rules) & fired
    }
    assert not missing, f"Kural kataloğunun kaçırdığı beklenen bulgular: {missing}"


def test_rule_model_rejects_a_rule_without_sources() -> None:
    with pytest.raises(ValueError):
        Rule.model_validate(
            {
                "id": "R-TEST",
                "title": "t",
                "stride": "S",
                "base": {"likelihood": 1, "impact": 1},
                "description": "d",
                "scenario": "s",
                "knowledge_ids": [],
            }
        )


# --- negation handling ----------------------------------------------


def test_control_keyword_in_a_negative_sentence_is_not_evidence(
    model: SystemModel,
) -> None:
    """"... kontrolü yapılmaz" must not count as the control being present."""
    doc = (
        "Transfer Servisi, istek gövdesindeki hesap numarasının müşteriye ait "
        "olup olmadığını, yani hesap sahipliği kontrolünü yapmaz."
    )
    threat = next(t for t in evaluate(model, doc) if t.rule_id == "R-API-BOLA")
    assert threat.context.control_evidence is None


def test_control_keyword_in_a_positive_sentence_is_evidence(
    model: SystemModel,
) -> None:
    doc = "Transfer Servisi her istekte hesap sahipliği kontrolü uygular."
    threat = next(t for t in evaluate(model, doc) if t.rule_id == "R-API-BOLA")
    assert threat.context.control_evidence == "hesap sahipliği"


def test_missing_statement_is_not_read_as_a_control(model: SystemModel) -> None:
    doc = "Yedeklerin şifrelenip şifrelenmediği dokümanda belirtilmemiştir."
    threat = next(
        t for t in evaluate(model, doc) if t.rule_id == "R-DATA-BACKUP-ENCRYPTION"
    )
    assert threat.context.control_evidence is None


def test_keyword_does_not_match_inside_another_word(model: SystemModel) -> None:
    """"acl" must not match inside "Oracle"."""
    from app.rules.engine import _control_evidence
    from app.rules.schema import ContextAdjust, Rule

    rule = Rule.model_validate(
        {
            "id": "R-TEST-ACL",
            "title": "t",
            "stride": "T",
            "base": {"likelihood": 1, "impact": 1},
            "description": "d",
            "scenario": "s",
            "knowledge_ids": ["CWE-306"],
            "mitigations": ["M-X"],
            "context_adjust": {"evidence_of_control_keywords": ["acl"]},
        }
    )
    assert _control_evidence(rule, normalise("İşlem Veritabanı Oracle 19c")) is None
    assert _control_evidence(rule, normalise("Kuyrukta acl tanımlıdır")) == "acl"
    assert isinstance(rule.context_adjust, ContextAdjust)


def test_a_planned_control_is_not_an_existing_control(model: SystemModel) -> None:
    doc = (
        "Limit sayacı güncellemesinin atomik olarak yapılması "
        "performans testlerinden sonra gözden geçirilecektir."
    )
    threat = next(t for t in evaluate(model, doc) if t.rule_id == "R-PAY-RACE-LIMIT")
    assert threat.context.control_evidence is None


def test_unbounded_keyword_match_is_rejected(model: SystemModel) -> None:
    """A regex keyword must not span the whole (single-line) document."""
    from app.rules.engine import MAX_CONTROL_SPAN, _control_evidence
    from app.rules.schema import Rule

    rule = Rule.model_validate(
        {
            "id": "R-TEST-SPAN",
            "title": "t",
            "stride": "S",
            "base": {"likelihood": 1, "impact": 1},
            "description": "d",
            "scenario": "s",
            "knowledge_ids": ["CWE-307"],
            "mitigations": ["M-X"],
            "context_adjust": {"evidence_of_control_keywords": ["basla.*bitis"]},
        }
    )
    far_apart = normalise("basla " + ("x " * (MAX_CONTROL_SPAN // 2 + 40)) + " bitis")
    assert _control_evidence(rule, far_apart) is None
    assert _control_evidence(rule, normalise("basla ve bitis")) == "basla.*bitis"


# --- The catalogue's own citations must resolve -----------------------


def _knowledge_identifiers() -> set[str]:
    from app.kb.loader import read_entries

    return {entry["identifier"] for entry in read_entries()}


def test_every_cited_source_exists_in_the_knowledge_base() -> None:
    """A rule citing an identifier we do not have loses that citation.

    Step 5 drops unknown identifiers as fabricated, so a typo here would
    quietly strip the rule's source instead of failing loudly.
    """
    known = _knowledge_identifiers()
    missing = {
        rule.id: sorted(set(rule.knowledge_ids) - known)
        for rule in load_catalog()
        if set(rule.knowledge_ids) - known
    }
    assert not missing, f"bilgi tabanında olmayan kaynak: {missing}"


def test_every_suggested_mitigation_exists_in_the_control_catalogue() -> None:
    from app.controls.catalog import load_mitigations

    known = set(load_mitigations())
    missing = {
        rule.id: sorted(set(rule.mitigations) - known)
        for rule in load_catalog()
        if set(rule.mitigations) - known
    }
    assert not missing, f"önlem kataloğunda olmayan önlem: {missing}"
