"""Schema for the per-threat mitigation text the LLM writes in step 7."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MitigationText(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mitigation_id: str = Field(max_length=80)
    text: str = Field(max_length=1200)
    effort: Literal["düşük", "orta", "yüksek"] | None = None


class MitigationTextList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    mitigations: list[MitigationText] = Field(default_factory=list)
