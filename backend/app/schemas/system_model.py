"""The system model extracted from the architecture document.

Field names are English (code convention); the UI labels them in Turkish.

Two rules are enforced here rather than trusted to the model:
  * anything the document does not state stays ``unknown`` - the LLM must not
    guess (see ``Unknown`` / ``MaybeBool`` below);
  * every component and flow carries evidence: a short quote plus where it
    came from. Items without evidence are surfaced as assumptions.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ComponentType = Literal[
    "web_app",
    "mobile_app",
    "api",
    "service",
    "database",
    "queue",
    "external",
    "gateway",
    "auth",
    "admin",
    "llm",
    "other",
]

Sensitivity = Literal["low", "medium", "high", "unknown"]

# Tri-state: the document says yes, says no, or does not say.
MaybeBool = bool | Literal["unknown"]


class Evidence(BaseModel):
    """A short quote from the document plus where it was found."""

    model_config = ConfigDict(extra="ignore")

    quote: str = Field(max_length=400)
    page: int | None = None
    section: str | None = None

    @field_validator("quote")
    @classmethod
    def _trim(cls, value: str) -> str:
        return " ".join(value.split())


class Component(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(max_length=80)
    name: str = Field(max_length=200)
    type: ComponentType = "other"
    technology: str | None = None
    trust_zone: str | None = None
    internet_facing: MaybeBool = "unknown"
    authentication: str | None = None
    description: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class DataFlow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(max_length=80)
    source_id: str = Field(max_length=80)
    target_id: str = Field(max_length=80)
    protocol: str | None = None
    encrypted: MaybeBool = "unknown"
    authenticated: MaybeBool = "unknown"
    data_classes: list[str] = Field(default_factory=list)
    description: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)


class TrustZone(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str = Field(max_length=80)
    name: str = Field(max_length=200)
    description: str | None = None


class DataClass(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(max_length=120)
    sensitivity: Sensitivity = "unknown"
    description: str | None = None


class Role(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(max_length=120)
    permissions: str | None = None


class Assumption(BaseModel):
    model_config = ConfigDict(extra="ignore")

    text: str
    reason: str | None = None


class Unknown(BaseModel):
    """Something important the document does not state."""

    model_config = ConfigDict(extra="ignore")

    text: str
    # Why it matters for threat modelling.
    impact: str | None = None


class SystemModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    components: list[Component] = Field(default_factory=list)
    data_flows: list[DataFlow] = Field(default_factory=list)
    trust_zones: list[TrustZone] = Field(default_factory=list)
    data_classes: list[DataClass] = Field(default_factory=list)
    roles: list[Role] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    unknowns: list[Unknown] = Field(default_factory=list)

    def component_ids(self) -> set[str]:
        return {component.id for component in self.components}

    def dangling_flows(self) -> list[DataFlow]:
        """Flows whose endpoints are not in the component list."""
        ids = self.component_ids()
        return [
            flow
            for flow in self.data_flows
            if flow.source_id not in ids or flow.target_id not in ids
        ]

    def without_evidence(self) -> list[str]:
        """Ids of components and flows that carry no evidence quote."""
        missing = [c.id for c in self.components if not c.evidence]
        missing += [f.id for f in self.data_flows if not f.evidence]
        return missing


def merge_models(models: list[SystemModel]) -> SystemModel:
    """Merge the per-chunk results of a long document into one model.

    First occurrence wins for scalar fields; evidence is accumulated, so a
    component mentioned in two sections keeps both quotes.
    """
    merged = SystemModel()
    components: dict[str, Component] = {}
    flows: dict[str, DataFlow] = {}
    zones: dict[str, TrustZone] = {}
    data_classes: dict[str, DataClass] = {}
    roles: dict[str, Role] = {}
    seen_assumptions: set[str] = set()
    seen_unknowns: set[str] = set()

    for model in models:
        for component in model.components:
            existing = components.get(component.id)
            if existing is None:
                components[component.id] = component.model_copy(deep=True)
            else:
                existing.evidence.extend(component.evidence)
                _fill_blanks(existing, component)
        for flow in model.data_flows:
            existing_flow = flows.get(flow.id)
            if existing_flow is None:
                flows[flow.id] = flow.model_copy(deep=True)
            else:
                existing_flow.evidence.extend(flow.evidence)
                _fill_blanks(existing_flow, flow)
        for zone in model.trust_zones:
            zones.setdefault(zone.id, zone)
        for data_class in model.data_classes:
            data_classes.setdefault(data_class.name, data_class)
        for role in model.roles:
            roles.setdefault(role.name, role)
        for assumption in model.assumptions:
            if assumption.text not in seen_assumptions:
                seen_assumptions.add(assumption.text)
                merged.assumptions.append(assumption)
        for unknown in model.unknowns:
            if unknown.text not in seen_unknowns:
                seen_unknowns.add(unknown.text)
                merged.unknowns.append(unknown)

    merged.components = list(components.values())
    merged.data_flows = list(flows.values())
    merged.trust_zones = list(zones.values())
    merged.data_classes = list(data_classes.values())
    merged.roles = list(roles.values())
    return merged


def _fill_blanks(target: BaseModel, source: BaseModel) -> None:
    """Copy fields from ``source`` where ``target`` has nothing or 'unknown'."""
    for name in type(target).model_fields:
        if name in ("id", "evidence"):
            continue
        current = getattr(target, name)
        incoming = getattr(source, name)
        empty = current in (None, "", "unknown", []) or current == []
        if empty and incoming not in (None, "", "unknown", []):
            setattr(target, name, incoming)
