"""Deterministic stub client used by the test suite.

It is NOT a demo mode: it answers with a fixed, minimal payload so unit tests
can exercise validation, repair and recording without a network call. It is
only selected when ``LLM_PROVIDER=stub`` and the UI labels any run that used
it as a stub run.
"""

from __future__ import annotations

import json

from app.llm.base import LLMResponse


class StubClient:
    provider = "stub"

    def __init__(self, *, model: str = "stub-1", responses: list[str] | None = None):
        self.model = model
        # Successive answers; the last one repeats once exhausted.
        self._responses = responses or [json.dumps(_DEFAULT_PAYLOAD, ensure_ascii=False)]
        self.calls: list[dict] = []

    async def generate(
        self,
        *,
        system: str,
        user: str,
        images: list[bytes] | None = None,
        temperature: float = 0.2,
        json_output: bool = False,
        max_output_tokens: int | None = None,
    ) -> LLMResponse:
        index = min(len(self.calls), len(self._responses) - 1)
        self.calls.append({"system": system, "user": user, "images": len(images or [])})
        return LLMResponse(
            text=self._responses[index],
            prompt_tokens=100,
            completion_tokens=50,
            raw={"stub": True},
        )


_DEFAULT_PAYLOAD = {
    "components": [
        {
            "id": "c1",
            "name": "Örnek Servis",
            "type": "service",
            "internet_facing": "unknown",
            "evidence": [{"quote": "Örnek Servis isteği işler.", "page": 1}],
        }
    ],
    "data_flows": [],
    "trust_zones": [],
    "data_classes": [],
    "roles": [],
    "assumptions": [],
    "unknowns": [],
}
