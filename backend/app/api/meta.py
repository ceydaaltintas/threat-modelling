"""Metadata the frontend needs to render itself.

The step list lives in the backend so the stepper never hard-codes it.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import get_settings
from app.core.db import get_session
from app.core.samples import SAMPLE_SCENARIOS
from app.models import AnalysisRun, LlmCall, Project
from app.pipeline import MODEL_APPROVAL_AFTER_STEP, PIPELINE_STEPS
from app.schemas.api import MetaResponse, RiskThresholds, SampleScenarioOut, StepInfo

router = APIRouter(prefix="/api", tags=["meta"])

# Which build phase is implemented. The UI uses this to
# label placeholder data instead of pretending it is real output.
BUILD_PHASE = 4


@router.get("/meta", response_model=MetaResponse)
async def meta() -> MetaResponse:
    settings = get_settings()
    return MetaResponse(
        app_name=settings.app_name,
        app_env=settings.app_env,
        version=__version__,
        build_phase=BUILD_PHASE,
        steps=[
            StepInfo(
                no=s.no,
                name=s.name,
                description=s.description,
                performer=s.performer,
                counter_labels=s.counter_labels,
            )
            for s in PIPELINE_STEPS
        ],
        model_approval_after_step=MODEL_APPROVAL_AFTER_STEP,
        risk_thresholds=RiskThresholds(
            low=settings.risk_threshold_low,
            medium=settings.risk_threshold_medium,
            high=settings.risk_threshold_high,
        ),
        demo_replay=settings.demo_replay,
        ocr_enabled=settings.ocr_enabled,
        llm_provider=settings.llm_provider,
        llm_model=settings.llm_model,
        llm_configured=settings.llm_configured,
    )


@router.get("/samples", response_model=list[SampleScenarioOut])
async def samples() -> list[SampleScenarioOut]:
    return [
        SampleScenarioOut(
            key=s.key,
            title=s.title,
            doc_code=s.doc_code,
            summary=s.summary,
            focus=s.focus,
            filename=s.filename,
            available=s.available,
            size_bytes=s.size_bytes,
        )
        for s in SAMPLE_SCENARIOS
    ]


@router.get("/replay")
async def replay_status(session: AsyncSession = Depends(get_session)) -> dict:
    """How many recorded LLM answers exist, for the settings screen.

    Recorded output is what lets the demo run without internet. The screen
    says plainly whether recordings exist and which scenarios they cover.
    """
    settings = get_settings()
    total = (
        await session.execute(
            select(func.count())
            .select_from(LlmCall)
            .where(LlmCall.status == "ok", LlmCall.from_cache.is_(False))
        )
    ).scalar_one()
    by_prompt = dict(
        (
            await session.execute(
                select(LlmCall.prompt_name, func.count())
                .where(LlmCall.status == "ok", LlmCall.from_cache.is_(False))
                .group_by(LlmCall.prompt_name)
            )
        ).all()
    )
    sample_keys = (
        await session.execute(
            select(Project.sample_key, func.count(LlmCall.id))
            .join(AnalysisRun, AnalysisRun.project_id == Project.id)
            .join(LlmCall, LlmCall.run_id == AnalysisRun.id)
            .where(
                Project.sample_key.is_not(None),
                LlmCall.status == "ok",
                LlmCall.from_cache.is_(False),
            )
            .group_by(Project.sample_key)
        )
    ).all()

    return {
        "mode": settings.demo_replay,
        "recorded_calls": total,
        "by_prompt": {name or "—": count for name, count in by_prompt.items()},
        "by_sample": {key: count for key, count in sample_keys},
        "ready": total > 0,
        "note": (
            "Kayıtlı çıktı, daha önce gerçekten yapılmış LLM çağrılarının "
            "yanıtlarıdır. Kayıt yoksa canlı çağrı yapılır; mod 'strict' ise "
            "adım hata verir."
        ),
    }
