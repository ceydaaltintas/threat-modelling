"""Metadata the frontend needs to render itself.

The step list lives in the backend so the stepper never hard-codes it.
"""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.core.config import get_settings
from app.core.samples import SAMPLE_SCENARIOS
from app.pipeline import MODEL_APPROVAL_AFTER_STEP, PIPELINE_STEPS
from app.schemas.api import MetaResponse, RiskThresholds, SampleScenarioOut, StepInfo

router = APIRouter(prefix="/api", tags=["meta"])

# Which build phase of docs/PROMPT.md is implemented. The UI uses this to
# label placeholder data instead of pretending it is real output.
BUILD_PHASE = 1


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
