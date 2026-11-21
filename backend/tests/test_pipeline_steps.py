"""The step catalogue is the contract between backend and the UI stepper."""

from __future__ import annotations

import pytest

from app.pipeline import MODEL_APPROVAL_AFTER_STEP, PIPELINE_STEPS, step_by_no
from app.pipeline.mock_runner import PAUSE_AFTER_STEP


def test_there_are_exactly_nine_steps() -> None:
    assert len(PIPELINE_STEPS) == 9


def test_step_numbers_are_contiguous_and_ordered() -> None:
    assert [s.no for s in PIPELINE_STEPS] == list(range(1, 10))


def test_every_step_has_turkish_label_and_description() -> None:
    for step in PIPELINE_STEPS:
        assert step.name.strip()
        assert step.description.strip()
        assert step.performer in {"code", "llm", "code+llm", "human"}


def test_model_approval_pause_sits_after_step_two() -> None:
    assert MODEL_APPROVAL_AFTER_STEP == 2
    assert PAUSE_AFTER_STEP[MODEL_APPROVAL_AFTER_STEP] == "model_approval"


def test_expert_review_is_the_human_step() -> None:
    human = [s.no for s in PIPELINE_STEPS if s.performer == "human"]
    assert human == [8]


def test_step_by_no_raises_for_unknown_step() -> None:
    assert step_by_no(4).name == "Tehditler üretildi"
    with pytest.raises(KeyError):
        step_by_no(42)
