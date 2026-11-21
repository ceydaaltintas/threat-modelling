"""ORM entities for the threat modelling platform.

The schema is created in full in phase 0 so that later phases only fill it in.
Design notes:
  * Primary keys are UUID strings - stable across export/import and safe in URLs.
  * Flexible, nested structures (evidence, risk breakdown, counters) are JSONB.
  * The three kinds of value required by the product rules are kept apart on
    ``threat``: ``ai_proposed`` (LLM suggestion), ``system_calc`` (computed by
    code) and ``expert`` (human decision). Code never overwrites an expert
    decision and the LLM never writes to the database directly.
"""

from __future__ import annotations

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid

# Dimension of the local multilingual embedding model (e5-small class).
EMBEDDING_DIM = 384


class Project(Base, TimestampMixin):
    __tablename__ = "project"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    # Set when the project was created from one of the bundled sample scenarios.
    sample_key: Mapped[str | None] = mapped_column(String(100))

    documents: Mapped[list["Document"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    runs: Mapped[list["AnalysisRun"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class Document(Base, TimestampMixin):
    __tablename__ = "document"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(500), nullable=False)
    # pdf | docx | text | image
    doc_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # Where the uploaded file lives on disk (backend/uploads/<id><ext>).
    storage_path: Mapped[str | None] = mapped_column(String(1000))
    mime_type: Mapped[str | None] = mapped_column(String(150))
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    page_count: Mapped[int | None] = mapped_column(Integer)
    raw_text: Mapped[str | None] = mapped_column(Text)
    # [{"page": 1, "section": "4. Akis", "start": 0, "end": 1200}, ...]
    section_map: Mapped[list | None] = mapped_column(JSONB)
    extraction_note: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="documents")


class AnalysisRun(Base, TimestampMixin):
    __tablename__ = "analysis_run"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    project_id: Mapped[str] = mapped_column(
        ForeignKey("project.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # pending | running | waiting_user | done | failed | cancelled
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Provider/model/temperature actually used, for reproducibility.
    llm_settings: Mapped[dict | None] = mapped_column(JSONB)
    # false | true | strict - recorded per run so the report can state it.
    demo_replay: Mapped[str] = mapped_column(String(10), nullable=False, default="false")
    # When true the pipeline does not stop at the model approval pause.
    auto_continue: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    error_message: Mapped[str | None] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="runs")
    steps: Mapped[list["RunStep"]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        order_by="RunStep.step_no",
    )


class RunStep(Base, TimestampMixin):
    __tablename__ = "run_step"
    __table_args__ = (UniqueConstraint("run_id", "step_no", name="uq_run_step_no"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_no: Mapped[int] = mapped_column(Integer, nullable=False)
    # Turkish label shown in the stepper.
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # pending | running | done | failed | waiting_user | skipped
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    progress: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # {"components": 11, "threats": 37, ...}
    counters: Mapped[dict | None] = mapped_column(JSONB)
    message: Mapped[str | None] = mapped_column(Text)
    # Step specific payload for its detail panel (retrieved knowledge,
    # merge statistics, report links...). Not used for pipeline decisions.
    output: Mapped[dict | None] = mapped_column(JSONB)

    run: Mapped[AnalysisRun] = relationship(back_populates="steps")


class SystemModel(Base, TimestampMixin):
    __tablename__ = "system_model"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Validated against the SystemModel pydantic schema before it is stored.
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # ai | expert - who produced this version.
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="ai")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(120))


class Threat(Base, TimestampMixin):
    __tablename__ = "threat"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_run.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # rule | llm | merged
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    rule_id: Mapped[str | None] = mapped_column(String(80))
    component_ref: Mapped[str | None] = mapped_column(String(120), index=True)
    flow_ref: Mapped[str | None] = mapped_column(String(120))
    # S | T | R | I | D | E
    stride: Mapped[str] = mapped_column(String(2), nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    scenario: Mapped[str | None] = mapped_column(Text)
    # [{"quote": "...", "page": 2, "section": "5, 4. madde"}] - empty => assumption
    evidence: Mapped[list | None] = mapped_column(JSONB)
    # [{"id": "CWE-639", "title": "...", "url": "..."}]
    knowledge_sources: Mapped[list | None] = mapped_column(JSONB)
    # {"likelihood": 3, "impact": 5, "rationale": "..."} - suggestion only
    ai_proposed: Mapped[dict | None] = mapped_column(JSONB)
    # {"likelihood": 4, "impact": 5, "score": 20, "level": "Kritik",
    #  "breakdown": [{"label": "...", "delta": 1, "reason": "..."}]}
    system_calc: Mapped[dict | None] = mapped_column(JSONB)
    # {"status": "accepted", "likelihood": 3, "impact": 4, "note": "...",
    #  "by": "...", "at": "..."}
    expert: Mapped[dict | None] = mapped_column(JSONB)
    mitigations: Mapped[list | None] = mapped_column(JSONB)
    # [{"framework": "ISO 27001:2022", "id": "A.8.3", "verification": "needed"}]
    control_mappings: Mapped[list | None] = mapped_column(JSONB)
    # [{"code": "unknown_knowledge_id", "message": "..."}] - never silently dropped
    validation_notes: Mapped[list | None] = mapped_column(JSONB)
    # ok | flagged | not_run
    validation_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="not_run"
    )
    # pending | accepted | rejected | false_positive | edited
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    is_assumption: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Set when this threat was merged out in favour of another one.
    duplicate_of: Mapped[str | None] = mapped_column(String(36))

    __table_args__ = (
        Index("ix_threat_run_review", "run_id", "review_status"),
        Index("ix_threat_run_stride", "run_id", "stride"),
    )


class KbChunk(Base, TimestampMixin):
    __tablename__ = "kb_chunk"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    # attack | capec | cwe | owasp | stride | linddun | iso27001 | nist80053 |
    # asvs | tr_regulation
    source: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    # Public identifier shown in the UI, e.g. "CWE-89", "API1:2023", "T1566".
    identifier: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(String(5), nullable=False, default="tr")
    license: Mapped[str | None] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(600))
    # needed when a clause number could not be confirmed
    verification: Mapped[str | None] = mapped_column(String(20))
    tags: Mapped[list | None] = mapped_column(JSONB)
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    search_vector: Mapped[str | None] = mapped_column(TSVECTOR)

    __table_args__ = (
        UniqueConstraint("source", "identifier", "lang", name="uq_kb_source_ident"),
        Index("ix_kb_search_vector", "search_vector", postgresql_using="gin"),
    )


class LlmCall(Base, TimestampMixin):
    __tablename__ = "llm_call"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[str | None] = mapped_column(
        ForeignKey("analysis_run.id", ondelete="CASCADE"), index=True
    )
    step_no: Mapped[int | None] = mapped_column(Integer)
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120))
    # sha256 of system+user+schema+model; the replay cache key.
    prompt_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    prompt_name: Mapped[str | None] = mapped_column(String(120))
    request_payload: Mapped[dict | None] = mapped_column(JSONB)
    response_payload: Mapped[dict | None] = mapped_column(JSONB)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    completion_tokens: Mapped[int | None] = mapped_column(Integer)
    from_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    repair_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # ok | failed | quota_exceeded | schema_invalid
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ok")
    error_message: Mapped[str | None] = mapped_column(Text)


class AuditLog(Base):
    """Append-only audit trail. Rows are never updated or deleted."""

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    actor: Mapped[str] = mapped_column(String(120), nullable=False)
    # security_expert | manager | system
    actor_role: Mapped[str] = mapped_column(String(40), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    object_type: Mapped[str] = mapped_column(String(60), nullable=False)
    object_id: Mapped[str | None] = mapped_column(String(36), index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), index=True)
    old_value: Mapped[dict | None] = mapped_column(JSONB)
    new_value: Mapped[dict | None] = mapped_column(JSONB)
    reason: Mapped[str | None] = mapped_column(Text)
