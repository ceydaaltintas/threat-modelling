"""Adapter for OpenAI-compatible chat completion endpoints.

Covers Groq, OpenRouter, Ollama and Gemini's OpenAI compatibility layer.

Note: the compatibility layer's structured output does not always honour a
JSON schema, so we ask for JSON and validate with pydantic ourselves rather
than trusting the provider.
"""

from __future__ import annotations

import base64

import httpx

from app.llm.base import (
    LLMBusy,
    LLMNotConfigured,
    LLMQuotaExceeded,
    LLMResponse,
    LLMTooLarge,
    LLMTruncated,
    LLMUnavailable,
)

REQUEST_TIMEOUT = httpx.Timeout(120.0, connect=15.0)

# Some providers sit behind a bot filter that rejects requests with no
# User-Agent (Groq returns a Cloudflare 1010 for them). A generic client
# name is enough; never put anything identifying here.
USER_AGENT = "threat-modelling-platform/0.1"


def _retry_after(response: "httpx.Response") -> float | None:
    """Seconds the provider asked us to wait, if the header is usable."""
    raw = response.headers.get("retry-after")
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        # The header may be an HTTP date; backing off by our own schedule
        # is better than parsing that here.
        return None
    return value if value > 0 else None


def _quota_message(response: "httpx.Response") -> str:
    """What the provider said, rather than a guess.

    A 429 can be a per-minute rate limit (wait a moment) or a daily token
    budget (waiting will not help today). The body and the Retry-After
    header say which; without them the advice was misleading. Recorded
    output mode is only suggested where it can actually work: it answers
    from recordings, so it helps on a document that has been analysed
    before, not on a new one.
    """
    detail = ""
    try:
        body = response.json()
        detail = (body.get("error") or {}).get("message") or ""
    except Exception:  # noqa: BLE001 - the body may not be JSON at all
        detail = ""

    retry_after = response.headers.get("retry-after") or ""
    parts = ["LLM sağlayıcısı istek sınırına takıldı (HTTP 429)."]
    if detail:
        parts.append(f"Sağlayıcının mesajı: {detail.strip()}")
    if retry_after:
        parts.append(f"Sağlayıcı {retry_after} sn sonra tekrar denemeyi öneriyor.")
    else:
        parts.append(
            "Dakikalık bir sınırsa kısa bir bekleme yeter; günlük bir "
            "bütçeyse bugün açılmaz, başka bir model veya sağlayıcı gerekir."
        )
    parts.append(
        "Daha önce çalıştırılmış bir doküman için DEMO_REPLAY=true kayıtlardan "
        "cevap verir; yeni bir doküman için kayıt bulunmadığından işe yaramaz."
    )
    return " ".join(parts)


class OpenAICompatibleClient:
    provider = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        max_output_tokens: int = 0,
    ) -> None:
        if not base_url:
            raise LLMNotConfigured(
                "LLM_BASE_URL tanımlı değil. .env dosyasında sağlayıcı adresini "
                "belirtin."
            )
        if not model:
            raise LLMNotConfigured(
                "LLM_MODEL tanımlı değil. README'deki güncel model listesinden "
                "bir model seçip .env dosyasına yazın."
            )
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        # 0 means "use the provider default", which is often far too low for
        # a full system model (Groq caps completions at 3072 by default).
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
        budget = (
            self.max_output_tokens
            if max_output_tokens is None
            else max_output_tokens
        )
        content: list[dict] | str
        if images:
            content = [{"type": "text", "text": user}]
            for image in images:
                encoded = base64.b64encode(image).decode("ascii")
                content.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{encoded}"},
                    }
                )
        else:
            content = user

        payload: dict = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
        }
        if json_output:
            payload["response_format"] = {"type": "json_object"}
        if budget:
            payload["max_completion_tokens"] = budget

        headers = {
            "content-type": "application/json",
            "user-agent": USER_AGENT,
        }
        if self.api_key:
            headers["authorization"] = f"Bearer {self.api_key}"

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    headers=headers,
                )
        except httpx.HTTPError as exc:
            raise LLMUnavailable(
                "LLM sağlayıcısına ulaşılamadı. İnternet bağlantısını kontrol "
                "edin veya kayıtlı çıktı moduna geçin.",
                detail=str(exc),
            ) from exc

        if response.status_code == 429:
            # The provider knows which limit was hit and how long it lasts;
            # guessing "60 sn" was wrong whenever the limit was a daily one.
            raise LLMQuotaExceeded(
                _quota_message(response),
                detail=response.text[:500],
                retry_after=_retry_after(response),
            )
        if response.status_code == 413:
            raise LLMTooLarge(
                "İstek sağlayıcının boyut sınırını aştı (HTTP 413). Yanıt "
                "bütçesi küçültülerek yeniden denenecek; sürerse .env "
                "içindeki LLM_MAX_OUTPUT_TOKENS değerini düşürün veya daha "
                "küçük bir doküman kullanın.",
                detail=response.text[:500],
                max_output_tokens=budget,
            )
        if response.status_code in (502, 503, 504):
            raise LLMBusy(
                "Model şu anda yoğun (sağlayıcı "
                f"{response.status_code} döndürdü). Birkaç saniye sonra "
                "otomatik olarak yeniden denenecek.",
                detail=response.text[:500],
            )
        if response.status_code in (401, 403):
            raise LLMNotConfigured(
                "LLM anahtarı reddedildi. .env dosyasındaki LLM_API_KEY değerini "
                "kontrol edin.",
                detail=response.text[:500],
            )
        if response.status_code >= 400:
            raise LLMUnavailable(
                f"LLM sağlayıcısı hata döndürdü (HTTP {response.status_code}).",
                detail=response.text[:500],
            )

        body = response.json()
        try:
            choice = body["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMUnavailable(
                "LLM yanıtı beklenen biçimde değil.", detail=str(body)[:500]
            ) from exc

        # A cut-off answer can still parse as JSON and look complete, which
        # would silently drop half the system model. Fail instead.
        if choice.get("finish_reason") == "length":
            raise LLMTruncated(
                "Model yanıtı token sınırına takıldı ve yarıda kesildi. "
                ".env içindeki LLM_MAX_OUTPUT_TOKENS değerini yükseltin "
                "veya dokümanı küçültün.",
                detail=f"finish_reason=length, model={body.get('model')}",
            )

        usage = body.get("usage") or {}
        return LLMResponse(
            text=text,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            raw={"id": body.get("id"), "model": body.get("model")},
        )
