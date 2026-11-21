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
    """docs/PROMPT.md: 'seviye değiştirme gerekçesi zorunlu'."""
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
