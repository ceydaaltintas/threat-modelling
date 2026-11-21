"""Risk scoring: the LLM proposes, this module decides."""

from __future__ import annotations

import pytest

from app.risk.scoring import STRIDE_BASE, Thresholds, score_threat


@pytest.fixture
def thresholds() -> Thresholds:
    return Thresholds(low=4, medium=9, high=16)


def context(**overrides) -> dict:
    base = {
        "base_likelihood": 3,
        "base_impact": 4,
        "confidence": "confirmed",
        "internet_facing": False,
        "sensitive_data": False,
        "data_classes": [],
        "control_evidence": None,
        "context_adjust": {},
    }
    base.update(overrides)
    return base


def test_score_is_likelihood_times_impact(thresholds) -> None:
    result = score_threat(
        stride="E", rule_context=context(), has_evidence=True, thresholds=thresholds
    )
    assert result.likelihood == 3
    assert result.impact == 4
    assert result.score == 12


@pytest.mark.parametrize(
    ("score_pair", "expected"),
    [((1, 2), "Düşük"), ((2, 3), "Orta"), ((3, 4), "Yüksek"), ((5, 5), "Kritik")],
)
def test_thresholds_map_scores_to_levels(thresholds, score_pair, expected) -> None:
    likelihood, impact = score_pair
    result = score_threat(
        stride="I",
        rule_context=context(base_likelihood=likelihood, base_impact=impact),
        has_evidence=True,
        thresholds=thresholds,
    )
    assert result.level == expected


def test_internet_facing_raises_likelihood(thresholds) -> None:
    plain = score_threat(
        stride="E", rule_context=context(), has_evidence=True, thresholds=thresholds
    )
    exposed = score_threat(
        stride="E",
        rule_context=context(internet_facing=True),
        has_evidence=True,
        thresholds=thresholds,
    )
    assert exposed.likelihood == plain.likelihood + 1


def test_sensitive_data_raises_impact(thresholds) -> None:
    result = score_threat(
        stride="I",
        rule_context=context(sensitive_data=True, data_classes=["TCKN"]),
        has_evidence=True,
        thresholds=thresholds,
    )
    assert result.impact == 5
    assert any("TCKN" in a.reason for a in result.adjustments)


def test_control_evidence_lowers_likelihood(thresholds) -> None:
    result = score_threat(
        stride="D",
        rule_context=context(control_evidence="hız sınırı"),
        has_evidence=True,
        thresholds=thresholds,
    )
    assert result.likelihood == 2
    assert any("hız sınırı" in a.reason for a in result.adjustments)


def test_unverified_rule_match_is_damped(thresholds) -> None:
    confirmed = score_threat(
        stride="T",
        rule_context=context(confidence="confirmed"),
        has_evidence=True,
        thresholds=thresholds,
    )
    possible = score_threat(
        stride="T",
        rule_context=context(confidence="possible"),
        has_evidence=True,
        thresholds=thresholds,
    )
    assert possible.likelihood == confirmed.likelihood - 1


def test_threat_without_evidence_is_damped(thresholds) -> None:
    result = score_threat(
        stride="S", rule_context=context(), has_evidence=False, thresholds=thresholds
    )
    assert result.likelihood == 2
    assert any("varsayım" in a.label.lower() for a in result.adjustments)


def test_values_are_clamped_to_one_and_five(thresholds) -> None:
    high = score_threat(
        stride="E",
        rule_context=context(
            base_likelihood=5, base_impact=5, internet_facing=True, sensitive_data=True
        ),
        has_evidence=True,
        thresholds=thresholds,
    )
    assert (high.likelihood, high.impact) == (5, 5)

    low = score_threat(
        stride="R",
        rule_context=context(base_likelihood=1, control_evidence="x"),
        has_evidence=False,
        thresholds=thresholds,
    )
    assert low.likelihood == 1


def test_llm_threat_uses_the_stride_baseline_not_the_model_suggestion(
    thresholds,
) -> None:
    """A threat with no rule behind it is scored from the STRIDE table."""
    result = score_threat(
        stride="E", rule_context=None, has_evidence=True, thresholds=thresholds
    )
    assert (result.base_likelihood, result.base_impact) == STRIDE_BASE["E"]
    assert "STRIDE" in result.explanation


def test_breakdown_is_explained_in_turkish(thresholds) -> None:
    result = score_threat(
        stride="E",
        rule_context=context(internet_facing=True, sensitive_data=True),
        has_evidence=True,
        thresholds=thresholds,
    )
    assert "Olasılık" in result.explanation
    assert "Etki" in result.explanation
    assert "Skor" in result.explanation
    # Every adjustment appears in the breakdown the UI renders.
    assert len(result.as_dict()["breakdown"]) == len(result.adjustments)


def test_custom_thresholds_are_respected() -> None:
    strict = Thresholds(low=2, medium=4, high=8)
    result = score_threat(
        stride="I",
        rule_context=context(base_likelihood=3, base_impact=3),
        has_evidence=True,
        thresholds=strict,
    )
    assert result.score == 9
    assert result.level == "Kritik"
