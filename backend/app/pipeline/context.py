"""Per-run context handed to each step module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import Settings
from app.llm.gateway import LLMGateway
from app.pipeline import progress
from app.pipeline.steps import StepDefinition


@dataclass
class RunContext:
    run_id: str
    project_id: str
    settings: Settings
    # Built lazily: a run that never reaches an LLM step needs no provider.
    gateway: LLMGateway | None = None
    counters: dict[str, int] | None = None
    # Panel payload each step wants persisted, keyed by step number.
    step_output: dict[int, dict] = field(default_factory=dict)

    async def report(
        self,
        step: StepDefinition,
        *,
        progress_value: float,
        message: str,
        counters: dict[str, int] | None = None,
    ) -> None:
        """Persist and publish mid-step progress."""
        llm = (
            self.gateway.usage.as_event(
                replay=self.settings.demo_replay != "false"
            )
            if self.gateway
            else {}
        )
        await progress.save_step(
            self.run_id,
            step.no,
            status="running",
            progress=progress_value,
            message=message,
            counters=counters,
        )
        await progress.publish_step(
            self.run_id,
            step,
            "running",
            progress=progress_value,
            message=message,
            counters=counters,
            llm=llm,
        )

    def llm_event(self) -> dict[str, Any]:
        if not self.gateway:
            return {}
        return self.gateway.usage.as_event(
            replay=self.settings.demo_replay != "false"
        )


class StepFailed(Exception):
    """Raised by a step with a Turkish, actionable message for the UI."""

    def __init__(self, message: str, *, detail: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
