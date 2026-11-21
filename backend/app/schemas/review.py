"""Schemas for the expert review step."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ReviewAction = Literal["accept", "reject", "false_positive", "edit", "reset"]

ACTION_LABELS: dict[str, str] = {
    "accept": "Kabul edildi",
    "reject": "Reddedildi",
    "false_positive": "Yanlış pozitif olarak işaretlendi",
    "edit": "Düzenlendi",
    "reset": "Karar geri alındı",
}

# What each action leaves on threat.review_status.
ACTION_STATUS: dict[str, str] = {
    "accept": "accepted",
    "reject": "rejected",
    "false_positive": "false_positive",
    "edit": "edited",
    "reset": "pending",
}


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: ReviewAction
    note: str | None = Field(default=None, max_length=2000)
    # Only for "edit": the expert's own likelihood/impact.
    likelihood: int | None = Field(default=None, ge=1, le=5)
    impact: int | None = Field(default=None, ge=1, le=5)
    # Mandatory when the expert changes the level.
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _check_edit(self) -> "ReviewRequest":
        if self.action == "edit":
            if self.likelihood is None and self.impact is None:
                raise ValueError(
                    "Düzenleme için olasılık veya etki değeri verilmelidir."
                )
            if not (self.reason or "").strip():
                raise ValueError(
                    "Seviye değişikliği için gerekçe zorunludur."
                )
        return self


class BulkReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threat_ids: list[str] = Field(min_length=1, max_length=500)
    action: Literal["accept", "reject", "false_positive", "reset"]
    note: str | None = Field(default=None, max_length=2000)


class ReviewSummary(BaseModel):
    pending: int = 0
    accepted: int = 0
    rejected: int = 0
    false_positive: int = 0
    edited: int = 0

    @property
    def decided(self) -> int:
        return self.accepted + self.rejected + self.false_positive + self.edited
