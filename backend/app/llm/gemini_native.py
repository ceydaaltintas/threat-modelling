"""Adapter for Gemini's own SDK (google-genai).

This is the default recommendation: structured output and image/PDF input are
more reliable here than through the OpenAI compatibility layer. The response
is still validated against the pydantic schema by the caller.
"""

from __future__ import annotations

import asyncio

from app.llm.base import (
    LLMBusy,
    LLMNotConfigured,
    LLMQuotaExceeded,
    LLMResponse,
    LLMUnavailable,
)


class GeminiNativeClient:
    provider = "gemini_native"

    def __init__(
        self, *, api_key: str, model: str, max_output_tokens: int = 0
    ) -> None:
        if not api_key:
            raise LLMNotConfigured(
                "LLM_API_KEY tanımlı değil. Gemini anahtarınızı .env dosyasına "
                "ekleyip servisleri yeniden başlatın."
            )
        if not model:
            raise LLMNotConfigured(
                "LLM_MODEL tanımlı değil. README'deki güncel model listesinden "
                "bir model seçip .env dosyasına yazın."
            )
        self.api_key = api_key
        self.model = model
        self.max_output_tokens = max_output_tokens

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
        # Imported lazily so the container starts even without the SDK.
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:  # pragma: no cover - dependency is pinned
            raise LLMNotConfigured(
                "google-genai paketi kurulu değil.", detail=str(exc)
            ) from exc

        client = genai.Client(api_key=self.api_key)

        parts: list = [user]
        for image in images or []:
            parts.append(types.Part.from_bytes(data=image, mime_type="image/png"))

        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json" if json_output else "text/plain",
            max_output_tokens=(
                self.max_output_tokens if max_output_tokens is None
                else max_output_tokens
            )
            or None,
        )

        def _call():
            return client.models.generate_content(
                model=self.model, contents=parts, config=config
            )

        try:
            # The SDK call is synchronous; keep the event loop free.
            response = await asyncio.to_thread(_call)
        except Exception as exc:  # noqa: BLE001 - mapped to our error types
            message = str(exc)
            lowered = message.lower()
            if "429" in message or "quota" in lowered or "resource_exhausted" in lowered:
                raise LLMQuotaExceeded(
                    "LLM sağlayıcısı istek sınırına takıldı. Dakikalık bir "
                    "sınırsa kısa bir bekleme yeter; günlük bir bütçeyse "
                    "bugün açılmaz, başka bir model veya sağlayıcı gerekir. "
                    "Daha önce çalıştırılmış bir doküman için DEMO_REPLAY=true "
                    "kayıtlardan cevap verir; yeni bir doküman için kayıt "
                    "bulunmadığından işe yaramaz.",
                    detail=message[:500],
                ) from exc
            if "503" in message or "unavailable" in lowered or "overload" in lowered:
                raise LLMBusy(
                    "Model şu anda yoğun (sağlayıcı 503 döndürdü). Birkaç "
                    "saniye sonra otomatik olarak yeniden denenecek.",
                    detail=message[:500],
                ) from exc
            if "api key" in lowered or "401" in message or "403" in message:
                raise LLMNotConfigured(
                    "LLM anahtarı reddedildi. .env dosyasındaki LLM_API_KEY "
                    "değerini kontrol edin.",
                    detail=message[:500],
                ) from exc
            raise LLMUnavailable(
                "LLM sağlayıcısına ulaşılamadı veya hata döndürdü.",
                detail=message[:500],
            ) from exc

        usage = getattr(response, "usage_metadata", None)
        return LLMResponse(
            text=response.text or "",
            prompt_tokens=getattr(usage, "prompt_token_count", None),
            completion_tokens=getattr(usage, "candidates_token_count", None),
            raw={"model": self.model},
        )
