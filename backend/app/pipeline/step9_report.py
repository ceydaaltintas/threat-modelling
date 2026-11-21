"""Step 9 - produce the reports.

PDF (executive report), Excel (every threat) and JSON (native + Open Threat
Model). The executive summary is drafted by the LLM when one is available
and is always labelled "AI üretti"; without a provider a plain generated
summary is used instead, so the step never fails for want of a key.

Files are written to the run's report directory and served by the API.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.core.db import SessionLocal
from app.llm.base import LLMError
from app.llm.prompts import load_prompt
from app.pipeline.context import RunContext, StepFailed
from app.pipeline.steps import step_by_no
from app.reports import data as report_data
from app.reports import excel as excel_report
from app.reports import json_export
from app.reports import pdf as pdf_report
from app.reports.storage import report_dir

logger = logging.getLogger(__name__)

STEP = step_by_no(9)
PROMPT_NAME = "executive_summary.v1"


def _fallback_summary(data: report_data.ReportData) -> str:
    """Used when no LLM is available. Plain facts, no interpretation."""
    critical = data.by_level.get("Kritik", 0)
    high = data.by_level.get("Yüksek", 0)
    top = ", ".join(t.title for t in data.top_threats[:3]) or "—"
    return (
        f"{data.project_name} için yapılan tehdit modelleme çalışmasında "
        f"{data.counts['components']} bileşen ve {data.counts['flows']} veri "
        f"akışı üzerinden {data.counts['total']} bulgu üretildi; "
        f"{data.counts['included']} tanesi bu raporda yer alıyor. "
        f"Bunların {critical} tanesi kritik, {high} tanesi yüksek seviyede "
        "değerlendirildi. "
        f"En çok dikkat isteyen konular: {top}. "
        f"{data.counts['assumptions']} bulgu dokümanda doğrudan kanıt "
        "bulunmadığı için varsayım olarak işaretlendi ve "
        f"{data.counts['pending']} bulgu için uzman kararı bekleniyor. "
        "Bulgular dokümandan türetilen olasılıklardır; sistem testiyle "
        "doğrulanmaları önerilir."
    )


# A summary is prose. Anything that looks like JSON, a code fence or a
# markdown document is a model that did not follow the prompt, and must not
# reach the report.
_NOT_PROSE = ("{", "[", "```", "<")


def _looks_like_prose(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 80:
        return False
    if stripped.startswith(_NOT_PROSE):
        return False
    # A few quoted keys are a strong sign of a JSON body.
    if stripped.count('":') >= 2:
        return False
    # Prose has sentences.
    return stripped.count(" ") >= 20 and ("." in stripped)


async def _draft_summary(ctx: RunContext, data: report_data.ReportData) -> tuple[str, bool]:
    if ctx.gateway is None:
        return _fallback_summary(data), False

    prompt = load_prompt(PROMPT_NAME)
    top = "\n".join(
        f"- {t.title} ({data.level_of(t)}, {data.component_name(t.component_ref)})"
        for t in data.top_threats
    ) or "-"
    unknowns = "\n".join(f"- {item.get('text')}" for item in data.unknowns[:6]) or "-"
    user = prompt.render(
        project_name=data.project_name,
        documents=", ".join(d["filename"] for d in data.documents) or "—",
        components=data.counts["components"],
        flows=data.counts["flows"],
        total=data.counts["total"],
        included=data.counts["included"],
        critical=data.by_level.get("Kritik", 0),
        high=data.by_level.get("Yüksek", 0),
        medium=data.by_level.get("Orta", 0),
        low=data.by_level.get("Düşük", 0),
        assumptions=data.counts["assumptions"],
        flagged=data.counts["flagged"],
        pending=data.counts["pending"],
        top_threats=top,
        unknowns=unknowns,
    )
    try:
        text = await ctx.gateway.generate_text(
            prompt_name=PROMPT_NAME,
            system=prompt.system,
            user=user,
            step_no=STEP.no,
        )
        if not _looks_like_prose(text):
            raise LLMError(
                "Model, yönetici özeti yerine beklenmeyen biçimde bir yanıt "
                "döndürdü."
            )
        return text.strip(), True
    except LLMError as exc:
        logger.warning("Yönetici özeti alınamadı: %s", exc.message)
        return _fallback_summary(data), False


async def run(ctx: RunContext) -> dict[str, int]:
    async with SessionLocal() as session:
        try:
            data = await report_data.collect(session, ctx.run_id)
        except ValueError as exc:
            raise StepFailed(str(exc)) from exc

    if not data.threats:
        raise StepFailed("Rapor üretilecek tehdit yok (4. adımı çalıştırın).")

    data.thresholds = {
        "low": ctx.settings.risk_threshold_low,
        "medium": ctx.settings.risk_threshold_medium,
        "high": ctx.settings.risk_threshold_high,
    }

    await ctx.report(STEP, progress_value=0.2, message="Yönetici özeti taslaklanıyor")
    data.summary_text, data.summary_is_ai = await _draft_summary(ctx, data)

    directory = report_dir(ctx.run_id)
    files: list[dict] = []

    await ctx.report(STEP, progress_value=0.45, message="PDF raporu üretiliyor")
    pdf_path = directory / "rapor.pdf"
    pdf_path.write_bytes(pdf_report.render_pdf(data))
    files.append({"kind": "pdf", "name": "rapor.pdf", "size": pdf_path.stat().st_size})

    await ctx.report(STEP, progress_value=0.7, message="Excel çıktısı yazılıyor")
    xlsx_path = directory / "tehditler.xlsx"
    xlsx_path.write_bytes(excel_report.build_workbook(data))
    files.append(
        {"kind": "excel", "name": "tehditler.xlsx", "size": xlsx_path.stat().st_size}
    )

    await ctx.report(STEP, progress_value=0.9, message="JSON çıktıları yazılıyor")
    native_path = directory / "analiz.json"
    native_path.write_text(
        json.dumps(json_export.build_native(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    files.append(
        {"kind": "json", "name": "analiz.json", "size": native_path.stat().st_size}
    )

    otm_path = directory / "otm.json"
    otm_path.write_text(
        json.dumps(json_export.build_otm(data), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    files.append({"kind": "otm", "name": "otm.json", "size": otm_path.stat().st_size})

    ctx.step_output[STEP.no] = {
        "files": files,
        "summary_text": data.summary_text,
        "summary_is_ai": data.summary_is_ai,
        "counts": data.counts,
        "by_level": data.by_level,
        "by_stride": data.by_stride,
        "by_component": data.by_component,
        "heatmap": data.heatmap,
        "thresholds": data.thresholds,
        "top_threats": [
            {
                "id": t.id,
                "title": t.title,
                "level": data.level_of(t),
                "score": data.score_of(t),
                "component": data.component_name(t.component_ref),
            }
            for t in data.top_threats
        ],
        "unknowns": data.unknowns,
    }
    return {"reports": len(files)}
