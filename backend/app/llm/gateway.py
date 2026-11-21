"""The only way the pipeline talks to an LLM.

Responsibilities:
  * build the prompt hash and, in recorded-output mode, answer from the
    database instead of calling the provider;
  * validate the answer against a pydantic schema and, on failure, feed the
    error back to the model for at most two repair attempts;
  * write one ``llm_call`` row per attempt (prompt hash, duration, tokens,
    cached or not, status) so the UI can show call counts and the
    "Önbellekten" badge honestly.

The LLM never writes to any other table.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import TypeVar

from pydantic import BaseModel, ValidationError

from app.core.config import Settings, get_settings
from app.core.db import SessionLocal
from app.llm.base import LLMClient, LLMError, LLMInvalidOutput, LLMResponse
from app.llm.json_utils import extract_json
from app.models import LlmCall

logger = logging.getLogger(__name__)

# Repair attempts after the first try; the third failure fails the step.
MAX_REPAIR_ATTEMPTS = 2

# Transient provider errors (429 rate limit, 503 overloaded) are retried
# with exponential backoff before the step is failed. Free tiers hit both
# regularly, and a demo must not die on a passing spike.
MAX_TRANSIENT_RETRIES = 3
BACKOFF_SECONDS = (4, 12, 30)

ModelT = TypeVar("ModelT", bound=BaseModel)


@dataclass
class LlmUsage:
    """Running totals published on the SSE stream."""

    calls: int = 0
    cached: int = 0
    tokens: int = 0
    repairs: int = 0
    # How many times we backed off and retried a transient provider error.
    waits: int = 0
    # Provider/model actually used, for the report.
    details: dict = field(default_factory=dict)

    def as_event(self, *, replay: bool) -> dict:
        return {
            "calls": self.calls,
            "cached": self.cached,
            "tokens": self.tokens,
            "repairs": self.repairs,
            "waits": self.waits,
            "replay": replay,
        }


def prompt_hash(
    *, provider: str, model: str, prompt_name: str, system: str, user: str, images: int
) -> str:
    digest = hashlib.sha256()
    for part in (provider, model, prompt_name, system, user, str(images)):
        digest.update(part.encode("utf-8"))
        digest.update(b"\x00")
    return digest.hexdigest()


class LLMGateway:
    def __init__(
        self,
        client: LLMClient,
        *,
        run_id: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.client = client
        self.run_id = run_id
        self.settings = settings or get_settings()
        self.usage = LlmUsage(
            details={"provider": client.provider, "model": client.model}
        )

    @property
    def replay_mode(self) -> str:
        return self.settings.demo_replay

    async def _call_with_backoff(
        self,
        *,
        system: str,
        user: str,
        images: list[bytes] | None,
        temperature: float,
        json_output: bool,
        on_wait: Callable[[int, float], Awaitable[None]] | None = None,
    ) -> LLMResponse:
        """Call the provider, backing off on transient errors."""
        last: LLMError | None = None
        for attempt in range(MAX_TRANSIENT_RETRIES + 1):
            try:
                return await self.client.generate(
                    system=system,
                    user=user,
                    images=images,
                    temperature=temperature,
                    json_output=json_output,
                )
            except LLMError as exc:
                last = exc
                if not exc.retryable or attempt == MAX_TRANSIENT_RETRIES:
                    raise
                delay = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
                self.usage.waits += 1
                logger.warning(
                    "Geçici LLM hatası (%s). %s sn sonra yeniden denenecek "
                    "(%s/%s).",
                    type(exc).__name__,
                    delay,
                    attempt + 1,
                    MAX_TRANSIENT_RETRIES,
                )
                if on_wait is not None:
                    await on_wait(attempt + 1, delay)
                await asyncio.sleep(delay)
        raise last if last else LLMError("Bilinmeyen LLM hatası.")

    async def generate_json(
        self,
        *,
        prompt_name: str,
        system: str,
        user: str,
        schema: type[ModelT],
        images: list[bytes] | None = None,
        step_no: int | None = None,
        temperature: float | None = None,
        on_wait: Callable[[int, float], Awaitable[None]] | None = None,
    ) -> ModelT:
        """Return a validated instance of ``schema`` or raise ``LLMError``."""
        temperature = (
            self.settings.llm_temperature if temperature is None else temperature
        )
        key = prompt_hash(
            provider=self.client.provider,
            model=self.client.model,
            prompt_name=prompt_name,
            system=system,
            user=user,
            images=len(images or []),
        )

        cached = await self._replay(key)
        if cached is not None:
            self.usage.calls += 1
            self.usage.cached += 1
            await self._record(
                key,
                prompt_name=prompt_name,
                step_no=step_no,
                duration_ms=0,
                response={"text": cached},
                status="ok",
                from_cache=True,
            )
            try:
                return schema.model_validate(extract_json(cached))
            except (ValueError, ValidationError) as exc:
                # A recorded answer that no longer validates is a bug, not a
                # user error - fall through to a live call.
                logger.warning("Kayıtlı yanıt doğrulanamadı: %s", exc)

        if self.replay_mode == "strict":
            raise LLMError(
                "Kayıtlı çıktı modu 'strict' ve bu istem için kayıt yok. "
                "scripts/seed_demo.py ile kayıtları üretin veya DEMO_REPLAY=true "
                "yapın."
            )

        conversation_user = user
        last_error: str | None = None

        for attempt in range(MAX_REPAIR_ATTEMPTS + 1):
            started = time.perf_counter()
            try:
                response = await self._call_with_backoff(
                    system=system,
                    user=conversation_user,
                    images=images,
                    temperature=temperature,
                    json_output=True,
                    on_wait=on_wait,
                )
            except LLMError as exc:
                await self._record(
                    key,
                    prompt_name=prompt_name,
                    step_no=step_no,
                    duration_ms=int((time.perf_counter() - started) * 1000),
                    response=None,
                    status=type(exc).__name__,
                    error=exc.detail or exc.message,
                    repair_attempts=attempt,
                )
                raise

            duration_ms = int((time.perf_counter() - started) * 1000)
            self.usage.calls += 1
            self.usage.tokens += (response.prompt_tokens or 0) + (
                response.completion_tokens or 0
            )

            try:
                parsed = schema.model_validate(extract_json(response.text))
            except (ValueError, ValidationError) as exc:
                last_error = _describe(exc)
                await self._record(
                    key,
                    prompt_name=prompt_name,
                    step_no=step_no,
                    duration_ms=duration_ms,
                    response=_response_payload(response),
                    status="schema_invalid",
                    error=last_error,
                    repair_attempts=attempt,
                )
                if attempt == MAX_REPAIR_ATTEMPTS:
                    break
                self.usage.repairs += 1
                conversation_user = _repair_prompt(user, response.text, last_error)
                continue

            await self._record(
                key,
                prompt_name=prompt_name,
                step_no=step_no,
                duration_ms=duration_ms,
                response=_response_payload(response),
                status="ok",
                repair_attempts=attempt,
            )
            return parsed

        raise LLMInvalidOutput(
            "LLM yanıtı beklenen şemaya uymadı (2 onarım denemesi yapıldı). "
            "Adımı yeniden deneyin veya modeli değiştirin.",
            detail=last_error,
        )

    async def generate_text(
        self,
        *,
        prompt_name: str,
        system: str,
        user: str,
        step_no: int | None = None,
    ) -> str:
        started = time.perf_counter()
        key = prompt_hash(
            provider=self.client.provider,
            model=self.client.model,
            prompt_name=prompt_name,
            system=system,
            user=user,
            images=0,
        )
        cached = await self._replay(key)
        if cached is not None:
            self.usage.calls += 1
            self.usage.cached += 1
            await self._record(
                key,
                prompt_name=prompt_name,
                step_no=step_no,
                duration_ms=0,
                response={"text": cached},
                status="ok",
                from_cache=True,
            )
            return cached

        if self.replay_mode == "strict":
            raise LLMError(
                "Kayıtlı çıktı modu 'strict' ve bu istem için kayıt yok. "
                "scripts/seed_demo.py ile kayıtları üretin veya DEMO_REPLAY=true "
                "yapın."
            )

        response = await self._call_with_backoff(
            system=system,
            user=user,
            images=None,
            temperature=self.settings.llm_temperature,
            json_output=False,
        )
        self.usage.calls += 1
        self.usage.tokens += (response.prompt_tokens or 0) + (
            response.completion_tokens or 0
        )
        await self._record(
            key,
            prompt_name=prompt_name,
            step_no=step_no,
            duration_ms=int((time.perf_counter() - started) * 1000),
            response=_response_payload(response),
            status="ok",
        )
        return response.text

    # --- recorded output ------------------------------------------------

    async def _replay(self, key: str) -> str | None:
        """The recorded answer for this exact prompt, if there is one.

        Only genuine live calls are replayed: a row that was itself written
        by a cache hit is skipped, so the cache can never feed on itself.
        """
        if self.replay_mode == "false":
            return None
        from sqlalchemy import select

        async with SessionLocal() as session:
            row = (
                await session.execute(
                    select(LlmCall)
                    .where(
                        LlmCall.prompt_hash == key,
                        LlmCall.status == "ok",
                        LlmCall.from_cache.is_(False),
                    )
                    .order_by(LlmCall.created_at.desc())
                    .limit(1)
                )
            ).scalar_one_or_none()
        if row is None or not row.response_payload:
            return None
        return row.response_payload.get("text")

    async def _record(
        self,
        key: str,
        *,
        prompt_name: str,
        step_no: int | None,
        duration_ms: int,
        response: dict | None,
        status: str,
        error: str | None = None,
        from_cache: bool = False,
        repair_attempts: int = 0,
    ) -> None:
        async with SessionLocal() as session:
            session.add(
                LlmCall(
                    run_id=self.run_id,
                    step_no=step_no,
                    provider=self.client.provider,
                    model=self.client.model,
                    prompt_hash=key,
                    prompt_name=prompt_name,
                    response_payload=response,
                    duration_ms=duration_ms,
                    prompt_tokens=(response or {}).get("prompt_tokens"),
                    completion_tokens=(response or {}).get("completion_tokens"),
                    from_cache=from_cache,
                    repair_attempts=repair_attempts,
                    status=status,
                    error_message=error,
                )
            )
            await session.commit()


def _response_payload(response: LLMResponse) -> dict:
    return {
        "text": response.text,
        "prompt_tokens": response.prompt_tokens,
        "completion_tokens": response.completion_tokens,
        **response.raw,
    }


def _describe(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        problems = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
            for err in exc.errors()[:8]
        ]
        return "; ".join(problems)
    return str(exc)


def _repair_prompt(original_user: str, bad_output: str, error: str) -> str:
    """Hand the validation error back to the model, once per attempt."""
    return (
        f"{original_user}\n\n"
        "--- ÖNCEKİ DENEME HATALI ---\n"
        "Aşağıdaki yanıtı verdin ancak şema doğrulamasından geçmedi.\n"
        f"Hata: {error}\n\n"
        "Hatalı yanıt:\n"
        f"{bad_output[:4000]}\n\n"
        "Yalnızca düzeltilmiş JSON'u döndür. Açıklama, başlık veya kod bloğu "
        "işareti ekleme."
    )
