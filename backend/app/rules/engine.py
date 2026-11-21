"""Run the YAML rule catalogue against a system model.

This is the deterministic half of threat generation: no LLM, no network, the
same input always produces the same findings. The LLM step adds context
specific threats on top.

Each generated threat carries the evidence of the component or flow it came
from, so a rule finding is traceable to the document just like an LLM one.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from app.rules.schema import Rule, RuleFile
from app.schemas.system_model import Component, DataFlow, SystemModel

logger = logging.getLogger(__name__)

CATALOG_DIR = Path(__file__).parent / "catalog"

# Data classes that raise impact; matched as substrings after normalisation.
SENSITIVE_DATA_HINTS = (
    "tckn",
    "kart",
    "iban",
    "pii",
    "kisisel",
    "gelir",
    "bakiye",
    "hesap",
    "kimlik",
    "biyometrik",
    "saglik",
)


def normalise(value: str) -> str:
    """Casefold and strip Turkish accents so keyword matching is forgiving."""
    folded = unicodedata.normalize("NFKD", value or "")
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("ı", "i").replace("İ", "i")
    return re.sub(r"\s+", " ", folded.casefold()).strip()


@dataclass
class ContextFlags:
    """What the code observed about this match; drives the risk breakdown."""

    internet_facing: bool = False
    sensitive_data: bool = False
    data_classes: list[str] = field(default_factory=list)
    # Keyword from the rule found in the document -> the control may exist.
    control_evidence: str | None = None


@dataclass
class RuleThreat:
    rule_id: str
    title: str
    stride: str
    description: str
    scenario: str
    knowledge_ids: list[str]
    mitigations: list[str]
    area: str
    component_ref: str | None
    flow_ref: str | None
    # Evidence copied from the matched model element.
    evidence: list[dict]
    base_likelihood: int
    base_impact: int
    context: ContextFlags
    # Serialised rule context_adjust, used by the risk step in phase 3.
    context_adjust: dict


@lru_cache(maxsize=1)
def load_catalog() -> tuple[Rule, ...]:
    rules: list[Rule] = []
    seen: set[str] = set()
    for path in sorted(CATALOG_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        try:
            parsed = RuleFile.model_validate(data)
        except Exception as exc:  # noqa: BLE001 - catalogue is ours, fail loud
            raise ValueError(f"{path.name}: kural dosyası geçersiz - {exc}") from exc
        for rule in parsed.rules:
            if rule.id in seen:
                raise ValueError(f"Tekrar eden kural kimliği: {rule.id}")
            seen.add(rule.id)
            rules.append(rule)
    logger.info("Kural kataloğu yüklendi: %s kural", len(rules))
    return tuple(rules)


def _haystack(*parts: str | None) -> str:
    return normalise(" ".join(part for part in parts if part))


def _any_in(needles: list[str], haystack: str) -> bool:
    return any(normalise(needle) in haystack for needle in needles)


def _component_data_classes(model: SystemModel, component: Component) -> list[str]:
    """Data classes that reach a component, through any flow it takes part in."""
    classes: list[str] = []
    for flow in model.data_flows:
        if component.id in (flow.source_id, flow.target_id):
            classes.extend(flow.data_classes)
    return sorted(set(classes))


def _matches_component(
    rule: Rule, model: SystemModel, component: Component, doc: str
) -> ContextFlags | None:
    applies = rule.applies_to
    if applies.component_type and component.type not in applies.component_type:
        return None
    if applies.internet_facing is not None:
        if component.internet_facing != applies.internet_facing:
            return None
    text = _haystack(
        component.name, component.technology, component.description, component.trust_zone
    )
    if applies.technology_any and not _any_in(applies.technology_any, text):
        return None
    if applies.name_any and not _any_in(applies.name_any, _haystack(component.name)):
        return None
    if applies.trust_zone_any and not _any_in(
        applies.trust_zone_any, _haystack(component.trust_zone)
    ):
        return None
    if applies.authentication_missing and component.authentication:
        return None

    data_classes = _component_data_classes(model, component)
    class_text = _haystack(" ".join(data_classes), component.description, component.name)
    if applies.data_class_any and not _any_in(applies.data_class_any, class_text):
        return None

    return ContextFlags(
        internet_facing=component.internet_facing is True,
        sensitive_data=_any_in(list(SENSITIVE_DATA_HINTS), class_text),
        data_classes=data_classes,
        control_evidence=_control_evidence(rule, doc),
    )


def _matches_flow(
    rule: Rule, model: SystemModel, flow: DataFlow, doc: str
) -> ContextFlags | None:
    applies = rule.applies_to
    if applies.encrypted is not None and flow.encrypted != applies.encrypted:
        return None
    if applies.authenticated is not None and flow.authenticated != applies.authenticated:
        return None
    if applies.protocol_any and not _any_in(
        applies.protocol_any, _haystack(flow.protocol)
    ):
        return None
    if applies.name_any and not _any_in(
        applies.name_any, _haystack(flow.description, flow.protocol)
    ):
        return None

    class_text = _haystack(" ".join(flow.data_classes), flow.description)
    if applies.data_class_any and not _any_in(applies.data_class_any, class_text):
        return None

    endpoints = {c.id: c for c in model.components}
    source = endpoints.get(flow.source_id)
    target = endpoints.get(flow.target_id)
    internet = any(
        c is not None and c.internet_facing is True for c in (source, target)
    )

    return ContextFlags(
        internet_facing=internet,
        sensitive_data=_any_in(list(SENSITIVE_DATA_HINTS), class_text),
        data_classes=list(flow.data_classes),
        control_evidence=_control_evidence(rule, doc),
    )


def _matches_system(rule: Rule, model: SystemModel, doc: str) -> ContextFlags | None:
    applies = rule.applies_to
    types = {component.type for component in model.components}
    if applies.system_has_component_type and not set(
        applies.system_has_component_type
    ) & types:
        return None
    if applies.document_mentions_any and not _any_in(
        applies.document_mentions_any, doc
    ):
        return None
    return ContextFlags(control_evidence=_control_evidence(rule, doc))


# Turkish negation markers. A control keyword inside a negative sentence
# means the opposite of what the keyword suggests: the document is saying the
# control is MISSING. Without this, "hesap sahipliği kontrolü yapılmaz" would
# be read as evidence that the control exists and would wrongly lower the
# risk score.
_NEGATION = re.compile(
    # Turkish negative verb suffixes after accent folding:
    #   yapmaz, yapilmaz, yapilmamaktadir, yapilmiyor, bulunmuyor,
    #   belirtilmemis, tanimlanmamis ...
    r"\b\w+m(?:[ae](?:z|mis|maktadir)|[aeiuo]yor)\b"
    # ... plus the standalone words that negate a statement ...
    r"|\b(?:yok|yoktur|degil|degildir|olmadan|eksik|mevcut degil|"
    r"belirtilmemis|tanimlanmamis|saglanmamaktadir)\b"
    # ... and the markers of something that is only planned or undecided.
    # A control that is going to be reviewed is not a control that exists.
    r"|\b(?:planlan\w*|degerlendirilecek\w*|gozden gecirilecek\w*|"
    r"tartisil\w*|karar verilmemis\w*|hedeflenmekte\w*|ilerleyen\w*)\b"
)
# How far around the keyword we look for a negation marker.
NEGATION_WINDOW = 90
# Keywords containing any of these are treated as regular expressions.
_REGEX_CHARS = re.compile(r"[.*+?{}\[\]()|\\^$]")

# The extracted document is one long line, so an unbounded ".*" in a keyword
# would match across the whole file. A control statement is a sentence, not a
# page: anything longer than this is not evidence.
MAX_CONTROL_SPAN = 120


def _is_negated(doc: str, start: int, end: int) -> bool:
    window = doc[max(0, start - NEGATION_WINDOW) : end + NEGATION_WINDOW]
    return bool(_NEGATION.search(window))


def _control_evidence(rule: Rule, doc: str) -> str | None:
    """The document hints the control may already be in place.

    A match inside a negative sentence is ignored - the document is then
    saying the control is absent, which is the finding, not a mitigation.
    """
    for keyword in rule.context_adjust.evidence_of_control_keywords:
        normalised = normalise(keyword)
        # Keywords may be written as small regexes (e.g. "otp.{0,60}deneme").
        # Plain phrases get word boundaries, otherwise "acl" would match
        # inside "Oracle".
        pattern = (
            normalised
            if _REGEX_CHARS.search(normalised)
            else rf"\b{re.escape(normalised)}\b"
        )
        try:
            match = re.search(pattern, doc)
        except re.error:
            index = doc.find(normalised)
            match = None
            if index != -1 and not _is_negated(doc, index, index + len(normalised)):
                return keyword
            continue
        if (
            match
            and (match.end() - match.start()) <= MAX_CONTROL_SPAN
            and not _is_negated(doc, match.start(), match.end())
        ):
            return keyword
    return None


def evaluate(model: SystemModel, document_text: str = "") -> list[RuleThreat]:
    """Apply every rule to every component, flow and the system as a whole."""
    doc = normalise(document_text)
    components = {component.id: component for component in model.components}
    threats: list[RuleThreat] = []

    for rule in load_catalog():
        if rule.target == "component":
            for component in model.components:
                context = _matches_component(rule, model, component, doc)
                if context is not None:
                    threats.append(
                        _build(rule, context, component_ref=component.id,
                               evidence=[e.model_dump(mode="json") for e in component.evidence])
                    )
        elif rule.target == "flow":
            for flow in model.data_flows:
                context = _matches_flow(rule, model, flow, doc)
                if context is not None:
                    threats.append(
                        _build(
                            rule,
                            context,
                            flow_ref=flow.id,
                            component_ref=flow.source_id
                            if flow.source_id in components
                            else None,
                            evidence=[e.model_dump(mode="json") for e in flow.evidence],
                            label=_flow_label(components, flow),
                        )
                    )
        else:
            context = _matches_system(rule, model, doc)
            if context is not None:
                threats.append(_build(rule, context, evidence=[]))

    return threats


def _flow_label(components: dict[str, Component], flow: DataFlow) -> str:
    source = components.get(flow.source_id)
    target = components.get(flow.target_id)
    return f"{source.name if source else flow.source_id} → {target.name if target else flow.target_id}"


def _build(
    rule: Rule,
    context: ContextFlags,
    *,
    component_ref: str | None = None,
    flow_ref: str | None = None,
    evidence: list[dict] | None = None,
    label: str | None = None,
) -> RuleThreat:
    title = f"{rule.title} — {label}" if label else rule.title
    return RuleThreat(
        rule_id=rule.id,
        title=title,
        stride=rule.stride,
        description=rule.description,
        scenario=rule.scenario,
        knowledge_ids=list(rule.knowledge_ids),
        mitigations=list(rule.mitigations),
        area=rule.area,
        component_ref=component_ref,
        flow_ref=flow_ref,
        evidence=evidence or [],
        base_likelihood=rule.base.likelihood,
        base_impact=rule.base.impact,
        context=context,
        context_adjust=rule.context_adjust.model_dump(mode="json"),
    )


def catalog_summary() -> dict:
    rules = load_catalog()
    by_area: dict[str, int] = {}
    for rule in rules:
        by_area[rule.area] = by_area.get(rule.area, 0) + 1
    return {
        "total": len(rules),
        "by_area": by_area,
        "knowledge_ids": sorted({kid for rule in rules for kid in rule.knowledge_ids}),
    }
