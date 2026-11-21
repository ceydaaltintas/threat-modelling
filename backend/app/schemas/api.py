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
    output: dict | None = None


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
    loaded: bool
    # Entries whose clause number the expert still has to confirm.
    verification_needed: int = 0
    licenses: dict[str, str] = {}
    embedding_model: str = ""
    # False when the local model could not be loaded; search falls back to
    # keyword only and says so.
    vector_search: bool = False


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    doc_type: str
    size_bytes: int | None
    page_count: int | None
    extraction_note: str | None
    section_map: list | None
    raw_text: str | None


class SystemModelOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    version: int
    source: str
    data: dict
    approved_at: datetime | None
    approved_by: str | None
    created_at: datetime


class SystemModelUpdate(BaseModel):
    """An expert edit of the extracted model."""

    data: dict
    reason: str | None = None
