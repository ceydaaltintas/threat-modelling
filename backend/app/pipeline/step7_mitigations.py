"""Step 7 - propose mitigations and map them to control frameworks.

Which mitigations apply is decided by code: rule threats carry them from the
rule, LLM threats get a set derived from their STRIDE category and context.
The LLM only writes the system specific wording for each one, and a threat
that gets no LLM text keeps the catalogue's generic text - so the step works
with no provider at all.

Control framework mapping (ISO 27001:2022, NIST SP 800-53, OWASP ASVS) comes
from the catalogue, never from the model. ISO entries stay flagged
"doğrulanacak".
"""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.controls import catalog as controls_catalog
from app.core.db import SessionLocal
from app.llm.base import LLMError
from app.llm.prompts import load_prompt
from app.models import SystemModel as SystemModelRow, Threat
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.steps import step_by_no
from app.schemas.mitigations import MitigationTextList
from app.schemas.system_model import SystemModel

logger = logging.getLogger(__name__)

STEP = step_by_no(7)
PROMPT_NAME = "mitigation_text.v1"

# Fallback mitigations per STRIDE, used for threats with no rule behind them.
STRIDE_MITIGATIONS: dict[str, list[str]] = {
    "S": ["M-STRONG-MFA", "M-TOKEN-LIFETIME", "M-MONITORING"],
    "T": ["M-SERVER-SIDE-LIMIT", "M-TLS-EVERYWHERE", "M-AUDIT-TRAIL"],
    "R": ["M-AUDIT-TRAIL", "M-INDIVIDUAL-ACCOUNTS", "M-DECISION-LOG"],
    "I": ["M-MASKING", "M-LEAST-PRIVILEGE", "M-LOG-MASKING"],
    "D": ["M-RATE-LIMIT", "M-QUOTA", "M-MONITORING"],
    "E": ["M-AUTHZ-OBJECT", "M-LEAST-PRIVILEGE", "M-AUDIT-TRAIL"],
}
# Only the worst threats are worth an LLM call; the rest keep the catalogue
# text. Keeps the free tier's quota for where it matters.
LLM_LEVELS = {"Kritik", "Yüksek"}
MAX_LLM_CALLS = 12


def _technologies(model: SystemModel) -> str:
    values = sorted(
        {
            component.technology.strip()
            for component in model.components
            if component.technology
        }
    )
    return ", ".join(values) or "belirtilmemiş"


def _mitigation_ids(threat: Threat) -> list[str]:
    existing = [
        item["id"] for item in (threat.mitigations or []) if item.get("id")
    ]
    if existing:
        return existing
    return STRIDE_MITIGATIONS.get(threat.stride, ["M-MONITORING"])


async def run(ctx: RunContext) -> dict[str, int]:
    catalog = controls_catalog.load_mitigations()

    async with SessionLocal() as session:
        model_row = (
            await session.execute(
                select(SystemModelRow)
                .where(SystemModelRow.run_id == ctx.run_id)
                .order_by(SystemModelRow.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if model_row is None:
            raise StepFailed("Önce sistem modelinin çıkarılması gerekir (2. adım).")
        model = SystemModel.model_validate(model_row.data)
        names = {component.id: component.name for component in model.components}
        technologies = _technologies(model)

        threats = (
            await session.execute(
                select(Threat)
                .where(Threat.run_id == ctx.run_id)
                .order_by(Threat.created_at)
            )
        ).scalars().all()
        if not threats:
            raise StepFailed("Önlem önerilecek tehdit yok (4. adımı çalıştırın).")

        # Worst first, so the LLM budget goes to the threats that matter.
        ordered = sorted(
            threats,
            key=lambda t: -((t.system_calc or {}).get("score") or 0),
        )

        prompt = load_prompt(PROMPT_NAME)
        written = 0
        llm_calls = 0
        mapped = 0
        unknown = 0
        llm_note: str | None = None

        # Say the work has started and how big it is. Without this the rail
        # sat on "Başlatılıyor…" for minutes whenever the provider was rate
        # limiting, because progress was only reported every tenth threat.
        await ctx.report(
            STEP,
            progress_value=0.0,
            message=f"Önlemler hazırlanıyor 0/{len(ordered)}",
            counters={"mitigations": 0, "mapped": 0},
        )

        for index, threat in enumerate(ordered, start=1):
            ids = _mitigation_ids(threat)
            known = [mid for mid in ids if mid in catalog]
            unknown += len(ids) - len(known)
            if not known:
                known = STRIDE_MITIGATIONS.get(threat.stride, ["M-MONITORING"])

            texts: dict[str, dict] = {
                mid: {
                    "id": mid,
                    "title": catalog[mid].title,
                    "text": catalog[mid].text,
                    "effort": catalog[mid].effort,
                    "source": "catalog",
                }
                for mid in known
                if mid in catalog
            }

            level = (threat.system_calc or {}).get("level")
            wants_llm = (
                ctx.gateway is not None
                and level in LLM_LEVELS
                and llm_calls < MAX_LLM_CALLS
                and llm_note is None
            )
            if wants_llm:
                listing = "\n".join(
                    f"- {mid}: {catalog[mid].title} — {catalog[mid].text}"
                    for mid in texts
                )
                user = prompt.render(
                    technologies=technologies,
                    threat_title=threat.title,
                    threat_stride=threat.stride,
                    component=names.get(threat.component_ref or "", "sistem geneli"),
                    threat_description=threat.description or "",
                    threat_scenario=threat.scenario or "",
                    mitigation_list=listing,
                )
                async def _waiting(
                    attempt: int, delay: float, _i: int = index
                ) -> None:
                    # A rate limited provider can hold this step for half a
                    # minute at a time; silence looks like a hang.
                    await ctx.report(
                        STEP,
                        progress_value=_i / len(ordered),
                        message=(
                            f"Model yoğun; {int(delay)} sn sonra yeniden "
                            f"denenecek ({attempt}. deneme) — {_i}/{len(ordered)}"
                        ),
                    )

                try:
                    result = await ctx.gateway.generate_json(
                        prompt_name=PROMPT_NAME,
                        system=prompt.system,
                        user=user,
                        schema=MitigationTextList,
                        step_no=STEP.no,
                        on_wait=_waiting,
                    )
                    llm_calls += 1
                    for item in result.mitigations:
                        # The model may not invent mitigations.
                        if item.mitigation_id in texts:
                            texts[item.mitigation_id]["text"] = item.text
                            texts[item.mitigation_id]["source"] = "llm"
                            if item.effort:
                                texts[item.mitigation_id]["effort"] = item.effort
                            written += 1
                except LLMError as exc:
                    logger.warning("Önlem metni alınamadı: %s", exc.message)
                    llm_note = (
                        f"Önlem metinleri LLM ile zenginleştirilemedi: "
                        f"{exc.message} Katalog metinleri kullanıldı."
                    )

            threat.mitigations = list(texts.values())
            mappings = controls_catalog.control_mappings(list(texts))
            threat.control_mappings = mappings
            mapped += len(mappings)

            if index % 5 == 0 or index == len(ordered):
                await ctx.report(
                    STEP,
                    progress_value=index / len(ordered),
                    message=f"Önlemler hazırlanıyor {index}/{len(ordered)}",
                    counters={"mitigations": index, "mapped": mapped},
                )

        await session.commit()

    if ctx.gateway is None:
        llm_note = (
            "LLM sağlayıcısı yapılandırılmadığı için önlem metinleri katalog "
            "metinleriyle bırakıldı."
        )
    elif llm_calls and not written and llm_note is None:
        # Calls went out but nothing usable came back: say so rather than
        # leaving the panel showing "12 çağrı, 0 metin" with no explanation.
        llm_note = (
            f"{llm_calls} LLM çağrısı yapıldı ancak kullanılabilir önlem metni "
            "dönmedi (model, verilen önlem kimlikleri için metin üretmedi). "
            "Katalog metinleri kullanıldı."
        )

    ctx.step_output[STEP.no] = {
        "threats": len(threats),
        "llm_calls": llm_calls,
        "llm_written": written,
        "control_mappings": mapped,
        "unknown_mitigations": unknown,
        "llm_note": llm_note,
        "llm_budget": MAX_LLM_CALLS,
    }

    return {
        "mitigations": len(threats),
        "mapped": mapped,
        "llm_written": written,
    }
