"""LLM client interface and shared error types.

The platform rule is: the LLM proposes, code decides. Clients here only
produce text or JSON; they never touch the database.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


class LLMError(Exception):
    """Base class. ``message`` is Turkish and shown to the user.

    ``retryable`` marks the errors that usually pass on their own: the
    provider being busy or the rate limit being hit. The gateway backs off
    and tries again for those; everything else fails the step immediately.
    """

    retryable = False

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail


class LLMNotConfigured(LLMError):
    pass


class LLMQuotaExceeded(LLMError):
    """Rate limit or quota (HTTP 429)."""

    retryable = True


class LLMBusy(LLMError):
    """The provider is temporarily overloaded (HTTP 503)."""

    retryable = True


class LLMUnavailable(LLMError):
    pass


class LLMTooLarge(LLMError):
    """The request exceeded the provider's size limit (HTTP 413).

    Carries the output budget that was used, so the caller can retry with a
    smaller one before giving up.
    """

    def __init__(
        self,
        message: str,
        *,
        detail: str | None = None,
        max_output_tokens: int = 0,
    ) -> None:
        super().__init__(message, detail=detail)
        self.max_output_tokens = max_output_tokens


class LLMTruncated(LLMError):
    """The answer was cut off by the output token limit.

    Dangerous to ignore: a truncated system model can still parse and would
    silently lose components, so this always fails the step.
    """


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
        max_output_tokens: int | None = None,
    ) -> LLMResponse: ...
