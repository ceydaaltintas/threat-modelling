"""Request/response schemas for the REST API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StepInfo(BaseModel):
    no: int
    name: str
    description: str
    performer: str
    counter_labels: dict[str, str]


class RiskThresholds(BaseModel):
    low: int
    medium: int
    high: int


class MetaResponse(BaseModel):
    app_name: str
    app_env: str
    version: str
    # Phase of the build, so the UI can label placeholder data honestly.
    build_phase: int
    steps: list[StepInfo]
    model_approval_after_step: int
    risk_thresholds: RiskThresholds
    demo_replay: str
    ocr_enabled: bool
    llm_provider: str
    llm_model: str
    # Whether a key is present. The key itself is never returned.
    llm_configured: bool


class HealthResponse(BaseModel):
    status: str
    database: str
    migrations: str | None = None
    detail: str | None = None


class SampleScenarioOut(BaseModel):
    key: str
    title: str
    doc_code: str
    summary: str
    focus: str
    filename: str
    available: bool
    size_bytes: int | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    sample_key: str | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None
    sample_key: str | None
    created_at: datetime


class RunStepOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_no: int
    name: str
    status: str
    progress: float
    started_at: datetime | None
    finished_at: datetime | None
    counters: dict | None
    message: str | None


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    project_name: str | None = None
    status: str
    started_at: datetime | None
    finished_at: datetime | None
    demo_replay: str
    auto_continue: bool
    error_message: str | None
    steps: list[RunStepOut] = []


class RunCreate(BaseModel):
    project_name: str | None = None
    sample_key: str | None = None
    auto_continue: bool = False


class KbStatsOut(BaseModel):
    total_chunks: int
    by_source: dict[str, int]
    # True once phase 2 has loaded the knowledge base.
    loaded: bool
