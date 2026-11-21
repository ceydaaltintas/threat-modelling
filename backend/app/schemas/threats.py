"""Schema for the threats the LLM proposes in step 4."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.system_model import Evidence

Stride = Literal["S", "T", "R", "I", "D", "E"]


class LlmThreat(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(max_length=400)
    stride: Stride
    component_id: str | None = None
    flow_id: str | None = None
    description: str = ""
    scenario: str = ""
    evidence: list[Evidence] = Field(default_factory=list)
    knowledge_ids: list[str] = Field(default_factory=list)
    # Suggestion only - code computes the score.
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    rationale: str | None = None

    @field_validator("knowledge_ids")
    @classmethod
    def _clean_ids(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item and item.strip()]


class LlmThreatList(BaseModel):
    model_config = ConfigDict(extra="ignore")

    threats: list[LlmThreat] = Field(default_factory=list)
