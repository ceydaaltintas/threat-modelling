"""Application settings, read from environment variables only.

Secrets (API keys) are never written to the repository and never returned by
the API. The settings screen in the UI shows which provider is configured but
not the key itself.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DemoReplayMode = Literal["false", "true", "strict"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Product ---
    app_name: str = "Tehdit Modelleme Platformu"
    app_env: Literal["development", "production"] = "development"

    # --- Database ---
    database_url: str = (
        "postgresql+psycopg://threatmodel:threatmodel@db:5432/threatmodel"
    )

    # --- CORS ---
    cors_origins: str = "http://localhost:3000"

    # --- LLM (used from phase 1 onwards) ---
    llm_provider: str = "gemini_native"
    llm_model: str = ""
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_temperature: float = 0.2
    llm_max_output_tokens: int = 0

    # --- Demo safety ---
    demo_replay: DemoReplayMode = "false"

    # --- Document ingestion ---
    ocr_enabled: bool = False
    max_upload_mb: int = 25

    # --- Risk thresholds (likelihood x impact, 1..25) ---
    risk_threshold_low: int = Field(default=4, ge=1, le=25)
    risk_threshold_medium: int = Field(default=9, ge=1, le=25)
    risk_threshold_high: int = Field(default=16, ge=1, le=25)

    @field_validator("demo_replay", mode="before")
    @classmethod
    def _normalise_replay(cls, value: object) -> object:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            return value.strip().lower()
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def llm_configured(self) -> bool:
        """True when a key is present. The key itself is never exposed."""
        return bool(self.llm_api_key.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
