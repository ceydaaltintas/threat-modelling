"""Risk scoring.

Code decides the score. The LLM's proposal is stored and displayed next to
it, but never feeds into it - that is the platform's first principle.

score = likelihood x impact, both 1..5, so 1..25. Thresholds come from
settings (defaults 4 / 9 / 16).

Every adjustment is recorded in a breakdown the UI prints as a sentence, so
a number on screen can always be traced back to the reason behind it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Level = Literal["Düşük", "Orta", "Yüksek", "Kritik"]

MIN_VALUE = 1
MAX_VALUE = 5

# Baseline when a threat has no rule behind it (an LLM-proposed threat).
# Derived from what each STRIDE category usually costs a bank, not from the
# model's own suggestion.
STRIDE_BASE: dict[str, tuple[int, int]] = {
    "S": (3, 4),  # kimlik taklidi
    "T": (2, 4),  # veri/kod değiştirme
    "R": (2, 3),  # inkâr
    "I": (3, 4),  # bilgi sızması
    "D": (3, 3),  # hizmet kesintisi
    "E": (2, 5),  # yetki yükseltme
}
DEFAULT_BASE = (3, 3)


@dataclass
class Adjustment:
    label: str
    field: Literal["likelihood", "impact"]
    delta: int
    reason: str

    def as_dict(self) -> dict:
        return {
            "label": self.label,
            "field": self.field,
            "delta": self.delta,
            "reason": self.reason,
        }


@dataclass
class RiskResult:
    likelihood: int
    impact: int
    score: int
    level: Level
    base_likelihood: int
    base_impact: int
    adjustments: list[Adjustment] = field(default_factory=list)
    # Plain Turkish sentence the UI shows under the number.
    explanation: str = ""

    def as_dict(self) -> dict:
        return {
            "likelihood": self.likelihood,
            "impact": self.impact,
            "score": self.score,
            "level": self.level,
            "base_likelihood": self.base_likelihood,
            "base_impact": self.base_impact,
            "breakdown": [item.as_dict() for item in self.adjustments],
            "explanation": self.explanation,
        }


@dataclass
class Thresholds:
    low: int = 4
    medium: int = 9
    high: int = 16

    def level_for(self, score: int) -> Level:
        if score <= self.low:
            return "Düşük"
        if score <= self.medium:
            return "Orta"
        if score <= self.high:
            return "Yüksek"
        return "Kritik"


def _clamp(value: int) -> int:
    return max(MIN_VALUE, min(MAX_VALUE, value))


def score_threat(
    *,
    stride: str,
    rule_context: dict | None,
    has_evidence: bool,
    thresholds: Thresholds,
) -> RiskResult:
    """Compute likelihood, impact and level with a traceable breakdown."""
    if rule_context:
        base_likelihood = int(rule_context.get("base_likelihood") or DEFAULT_BASE[0])
        base_impact = int(rule_context.get("base_impact") or DEFAULT_BASE[1])
        base_reason = "Kural kataloğundaki taban değer"
    else:
        base_likelihood, base_impact = STRIDE_BASE.get(stride, DEFAULT_BASE)
        base_reason = (
            "Kural tabanı yok (LLM önerisi); STRIDE kategorisinin varsayılan "
            "taban değeri kullanıldı"
        )

    base_likelihood = _clamp(base_likelihood)
    base_impact = _clamp(base_impact)
    adjustments: list[Adjustment] = []

    context = rule_context or {}
    overrides = context.get("context_adjust") or {}

    # --- internet exposure ---
    if context.get("internet_facing"):
        delta = int((overrides.get("internet_facing") or {}).get("likelihood", 1))
        if delta:
            adjustments.append(
                Adjustment(
                    "İnternete açık",
                    "likelihood",
                    delta,
                    "Bileşen doğrudan internetten erişilebilir olduğu için "
                    "saldırgan erişimi kolaydır.",
                )
            )

    # --- sensitive data ---
    if context.get("sensitive_data"):
        delta = int((overrides.get("sensitive_data") or {}).get("impact", 1))
        classes = ", ".join(context.get("data_classes") or []) or "hassas veri"
        if delta:
            adjustments.append(
                Adjustment(
                    "Hassas veri",
                    "impact",
                    delta,
                    f"Akan veri sınıfları: {classes}.",
                )
            )

    # --- control mentioned in the document ---
    control = context.get("control_evidence")
    if control:
        delta = int((overrides.get("evidence_of_control") or {}).get("likelihood", -1))
        if delta:
            adjustments.append(
                Adjustment(
                    "Dokümanda önlem izi",
                    "likelihood",
                    delta,
                    f"Dokümanda “{control}” ifadesi geçiyor; önlem kısmen "
                    "uygulanmış olabilir. Uzman doğrulamalıdır.",
                )
            )

    # --- unverified match damping ---
    # A rule that fired on component type alone describes a plausible but
    # unconfirmed weakness; one that fired on an explicit fact in the model
    # (an unencrypted flow, say) does not get damped.
    if context and context.get("confidence") == "possible":
        adjustments.append(
            Adjustment(
                "Dokümanda doğrulanmadı",
                "likelihood",
                -1,
                "Kural yalnızca bileşen türüne göre eşleşti; zayıflığın var "
                "olduğu dokümanda doğrulanmadı.",
            )
        )

    # --- assumption damping ---
    if not has_evidence:
        adjustments.append(
            Adjustment(
                "Kanıtsız (varsayım)",
                "likelihood",
                -1,
                "Dokümanda bu tehdidi destekleyen alıntı yok; varsayım olarak "
                "değerlendirildiği için olasılık düşürüldü.",
            )
        )

    likelihood = _clamp(
        base_likelihood
        + sum(a.delta for a in adjustments if a.field == "likelihood")
    )
    impact = _clamp(
        base_impact + sum(a.delta for a in adjustments if a.field == "impact")
    )
    score = likelihood * impact
    level = thresholds.level_for(score)

    return RiskResult(
        likelihood=likelihood,
        impact=impact,
        score=score,
        level=level,
        base_likelihood=base_likelihood,
        base_impact=base_impact,
        adjustments=adjustments,
        explanation=_explain(
            base_likelihood, base_impact, adjustments, likelihood, impact, score,
            level, base_reason,
        ),
    )


def _explain(
    base_likelihood: int,
    base_impact: int,
    adjustments: list[Adjustment],
    likelihood: int,
    impact: int,
    score: int,
    level: str,
    base_reason: str,
) -> str:
    def part(kind: str, base: int, final: int) -> str:
        terms = [str(base)]
        for item in adjustments:
            if item.field == kind:
                sign = "+" if item.delta > 0 else "−"
                # Keep the label as written: Python's lower() turns the
                # Turkish "İ" into "i̇" (i + combining dot).
                terms.append(f"{sign} {abs(item.delta)} ({item.label})")
        return f"{kind_label(kind)} {' '.join(terms)} = {final}"

    return (
        f"{base_reason}. "
        f"{part('likelihood', base_likelihood, likelihood)}; "
        f"{part('impact', base_impact, impact)}. "
        f"Skor {likelihood} × {impact} = {score} → {level}."
    )


def kind_label(kind: str) -> str:
    return "Olasılık" if kind == "likelihood" else "Etki"
