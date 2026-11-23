"""Expert review rules: what the schema allows and what it refuses."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.review import (
    ACTION_LABELS,
    ACTION_STATUS,
    BulkReviewRequest,
    ReviewRequest,
)


def test_simple_decisions_need_nothing_else() -> None:
    for action in ("accept", "reject", "false_positive", "reset"):
        assert ReviewRequest(action=action).action == action


def test_level_change_requires_a_reason() -> None:
    """Ürün kuralı: seviye değiştirme gerekçesi zorunludur."""
    with pytest.raises(ValidationError) as info:
        ReviewRequest(action="edit", likelihood=5, impact=5)
    assert "gerekçe" in str(info.value).lower()


def test_level_change_requires_a_value() -> None:
    with pytest.raises(ValidationError):
        ReviewRequest(action="edit", reason="çünkü")


def test_level_change_with_reason_is_accepted() -> None:
    request = ReviewRequest(
        action="edit", likelihood=5, impact=4, reason="Etki yükseltildi."
    )
    assert request.likelihood == 5
    assert request.reason


def test_blank_reason_is_not_a_reason() -> None:
    with pytest.raises(ValidationError):
        ReviewRequest(action="edit", likelihood=2, reason="   ")


@pytest.mark.parametrize("value", [0, 6, -1])
def test_values_outside_one_to_five_are_refused(value: int) -> None:
    with pytest.raises(ValidationError):
        ReviewRequest(action="edit", likelihood=value, reason="gerekçe")


def test_unknown_action_is_refused() -> None:
    with pytest.raises(ValidationError):
        ReviewRequest(action="silme")


def test_every_action_maps_to_a_status_and_a_label() -> None:
    for action in ("accept", "reject", "false_positive", "edit", "reset"):
        assert action in ACTION_STATUS
        assert action in ACTION_LABELS
    assert ACTION_STATUS["reset"] == "pending"


# --- bulk ---------------------------------------------------------------


def test_bulk_needs_at_least_one_threat() -> None:
    with pytest.raises(ValidationError):
        BulkReviewRequest(threat_ids=[], action="accept")


def test_bulk_does_not_allow_level_editing() -> None:
    """Editing a level needs a per-threat reason, so it cannot be bulk."""
    with pytest.raises(ValidationError):
        BulkReviewRequest(threat_ids=["a"], action="edit")


def test_bulk_accepts_a_list_of_ids() -> None:
    request = BulkReviewRequest(
        threat_ids=["a", "b", "c"], action="accept", note="Toplu kabul"
    )
    assert len(request.threat_ids) == 3


# --- Changing a decision that is already recorded ----------------------


def test_a_first_decision_needs_no_reason() -> None:
    from app.api.threats import _requires_change_reason

    assert _requires_change_reason("pending", "accept", None) is False


def test_changing_a_decision_without_a_reason_is_refused() -> None:
    from app.api.threats import _requires_change_reason

    assert _requires_change_reason("accepted", "reject", None) is True
    assert _requires_change_reason("accepted", "reject", "   ") is True
    assert _requires_change_reason("accepted", "reset", None) is True


def test_changing_a_decision_with_a_reason_is_allowed() -> None:
    from app.api.threats import _requires_change_reason

    assert (
        _requires_change_reason("accepted", "reject", "kanıt yanlış okunmuş")
        is False
    )


def test_repeating_the_same_decision_is_not_a_change() -> None:
    """Re-accepting an accepted threat changes nothing, so it needs nothing."""
    from app.api.threats import _requires_change_reason

    assert _requires_change_reason("accepted", "accept", None) is False
