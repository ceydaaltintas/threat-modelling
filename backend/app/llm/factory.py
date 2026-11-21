"""Chooses the LLM adapter from configuration."""

from __future__ import annotations

from app.core.config import Settings, get_settings
from app.llm.base import LLMClient, LLMNotConfigured
from app.llm.gemini_native import GeminiNativeClient
from app.llm.openai_compatible import OpenAICompatibleClient
from app.llm.stub import StubClient

# Default endpoints for the providers we name in .env.example, used when
# LLM_BASE_URL is left empty.
KNOWN_BASE_URLS = {
    "groq": "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "ollama": "http://host.docker.internal:11434/v1",
    "gemini_openai": "https://generativelanguage.googleapis.com/v1beta/openai",
}


def build_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.strip().lower()

    if provider == "stub":
        return StubClient(model=settings.llm_model or "stub-1")

    if provider == "gemini_native":
        return GeminiNativeClient(
            api_key=settings.llm_api_key, model=settings.llm_model
        )

    if provider in ("openai_compatible", *KNOWN_BASE_URLS):
        base_url = settings.llm_base_url or KNOWN_BASE_URLS.get(provider, "")
        return OpenAICompatibleClient(
            base_url=base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
        )

    raise LLMNotConfigured(
        f"Bilinmeyen LLM sağlayıcı: '{settings.llm_provider}'. "
        "Geçerli değerler: gemini_native, openai_compatible, groq, openrouter, "
        "ollama."
    )
