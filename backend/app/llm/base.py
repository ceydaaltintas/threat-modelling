"""LLM client interface and shared error types.

The platform rule is: the LLM proposes, code decides. Clients here only
produce text or JSON; they never touch the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Base class. ``message`` is Turkish and shown to the user."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class LLMNotConfigured(LLMError):
    pass


class LLMQuotaExceeded(LLMError):
    pass


class LLMUnavailable(LLMError):
    pass


class LLMInvalidOutput(LLMError):
    """The model answered, but the answer did not match the schema."""


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    raw: dict = field(default_factory=dict)


@runtime_checkable
class LLMClient(Protocol):
    """Minimal surface every provider adapter implements."""

    provider: str
    model: str

    async def generate(
        self,
        *,
        system: str,
        user: str,
        images: list[bytes] | None = None,
        temperature: float = 0.2,
        json_output: bool = False,
    ) -> LLMResponse: ...
