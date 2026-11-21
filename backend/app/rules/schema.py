"""The YAML rule catalogue's schema.

A rule is a piece of expert knowledge written down once: "a component that
looks like this, in a system that looks like that, has this known threat".
Rules run without an LLM, so the baseline set of findings is reproducible and
explainable.

Matching is deliberately small and predictable - every matcher below is
documented, and anything a rule cannot express belongs in the LLM step
instead.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Stride = Literal["S", "T", "R", "I", "D", "E"]
Target = Literal["component", "flow", "system"]
# The tri-state used across the system model.
MaybeBool = bool | Literal["unknown"]


class AppliesTo(BaseModel):
    """All listed conditions must hold (AND); inside a list, any value (OR)."""

    model_config = ConfigDict(extra="forbid")

    # --- component targets ---
    component_type: list[str] = Field(default_factory=list)
    # true/false/"unknown": matches the component's internet_facing exactly.
    internet_facing: MaybeBool | None = None
    # Substring match (case/accent insensitive) over technology + description.
    technology_any: list[str] = Field(default_factory=list)
    # Substring match over the component or flow name.
    name_any: list[str] = Field(default_factory=list)
    trust_zone_any: list[str] = Field(default_factory=list)
    # Matches the component's own data classes (via flows it takes part in)
    # or the flow's data_classes.
    data_class_any: list[str] = Field(default_factory=list)
    # Component has no authentication recorded.
    authentication_missing: bool | None = None

    # --- flow targets ---
    encrypted: MaybeBool | None = None
    authenticated: MaybeBool | None = None
    protocol_any: list[str] = Field(default_factory=list)

    # --- system targets ---
    # The model must contain at least one component of each listed type.
    system_has_component_type: list[str] = Field(default_factory=list)
    # The document text must mention any of these.
    document_mentions_any: list[str] = Field(default_factory=list)


class Base(BaseModel):
    model_config = ConfigDict(extra="forbid")

    likelihood: int = Field(ge=1, le=5)
    impact: int = Field(ge=1, le=5)


class ContextAdjust(BaseModel):
    """Context corrections applied by the risk step (phase 3).

    Declared here so the rule stays the single place where the knowledge
    lives; the numbers are applied by code, never by the LLM.
    """

    model_config = ConfigDict(extra="forbid")

    # Applied when the matched component is internet facing.
    internet_facing: dict[str, int] = Field(default_factory=dict)
    # Applied when card data or personal data flows through.
    sensitive_data: dict[str, int] = Field(default_factory=dict)
    # If any of these appear in the document, the control is probably already
    # in place: likelihood is reduced and the reason is shown in the breakdown.
    evidence_of_control_keywords: list[str] = Field(default_factory=list)
    evidence_of_control: dict[str, int] = Field(
        default_factory=lambda: {"likelihood": -1}
    )


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^R-[A-Z0-9-]+$")
    title: str
    target: Target = "component"
    applies_to: AppliesTo = Field(default_factory=AppliesTo)
    stride: Stride
    base: Base
    description: str
    scenario: str
    # Identifiers that must exist in the knowledge base; step 5 verifies them.
    knowledge_ids: list[str] = Field(default_factory=list)
    mitigations: list[str] = Field(default_factory=list)
    context_adjust: ContextAdjust = Field(default_factory=ContextAdjust)
    # Banking area, used for filtering and for the catalogue screen.
    area: str = "genel"

    @field_validator("knowledge_ids")
    @classmethod
    def _at_least_one_source(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError(
                "Her kural en az bir bilgi kaynağı kimliği taşımalıdır."
            )
        return value


class RuleFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rules: list[Rule]
