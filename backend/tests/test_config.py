from __future__ import annotations

from app.core.config import Settings


def test_demo_replay_accepts_boolean_like_values() -> None:
    assert Settings(demo_replay="TRUE").demo_replay == "true"
    assert Settings(demo_replay="strict").demo_replay == "strict"
    assert Settings(demo_replay="false").demo_replay == "false"


def test_cors_origins_are_split_and_trimmed() -> None:
    settings = Settings(cors_origins="http://a:3000, http://b:3000 ")
    assert settings.cors_origin_list == ["http://a:3000", "http://b:3000"]


def test_llm_configured_is_false_without_a_key() -> None:
    assert Settings(llm_api_key="").llm_configured is False
    assert Settings(llm_api_key="   ").llm_configured is False
    assert Settings(llm_api_key="abc").llm_configured is True
