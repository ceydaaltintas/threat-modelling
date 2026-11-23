"""Initial schema: projects, documents, runs, steps, system model, threats,
knowledge base, LLM calls and the audit trail.

The whole data model is created in phase 0, so
later phases only fill the tables in.

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384

_TS = sa.DateTime(timezone=True)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", _TS, server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", _TS, server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # pgvector must exist before the kb_chunk.embedding column is created.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    # Trigram index support for the duplicate/similarity checks in phase 3.
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "project",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("sample_key", sa.String(100)),
        *_timestamps(),
    )

    op.create_table(
        "document",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("doc_type", sa.String(20), nullable=False),
        sa.Column("mime_type", sa.String(150)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("page_count", sa.Integer()),
        sa.Column("raw_text", sa.Text()),
        sa.Column("section_map", postgresql.JSONB()),
        sa.Column("extraction_note", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_document_project_id", "document", ["project_id"])

    op.create_table(
        "analysis_run",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "project_id",
            sa.String(36),
            sa.ForeignKey("project.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("started_at", _TS),
        sa.Column("finished_at", _TS),
        sa.Column("llm_settings", postgresql.JSONB()),
        sa.Column("demo_replay", sa.String(10), nullable=False, server_default="false"),
        sa.Column(
            "auto_continue", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("error_message", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_analysis_run_project_id", "analysis_run", ["project_id"])

    op.create_table(
        "run_step",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("analysis_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("step_no", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
        sa.Column("started_at", _TS),
        sa.Column("finished_at", _TS),
        sa.Column("counters", postgresql.JSONB()),
        sa.Column("message", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("run_id", "step_no", name="uq_run_step_no"),
    )
    op.create_index("ix_run_step_run_id", "run_step", ["run_id"])

    op.create_table(
        "system_model",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("analysis_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("data", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="ai"),
        sa.Column("approved_at", _TS),
        sa.Column("approved_by", sa.String(120)),
        *_timestamps(),
    )
    op.create_index("ix_system_model_run_id", "system_model", ["run_id"])

    op.create_table(
        "threat",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("analysis_run.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("rule_id", sa.String(80)),
        sa.Column("component_ref", sa.String(120)),
        sa.Column("flow_ref", sa.String(120)),
        sa.Column("stride", sa.String(2), nullable=False),
        sa.Column("title", sa.String(400), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("scenario", sa.Text()),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("knowledge_sources", postgresql.JSONB()),
        sa.Column("ai_proposed", postgresql.JSONB()),
        sa.Column("system_calc", postgresql.JSONB()),
        sa.Column("expert", postgresql.JSONB()),
        sa.Column("mitigations", postgresql.JSONB()),
        sa.Column("control_mappings", postgresql.JSONB()),
        sa.Column("validation_notes", postgresql.JSONB()),
        sa.Column(
            "validation_status", sa.String(20), nullable=False, server_default="not_run"
        ),
        sa.Column(
            "review_status", sa.String(20), nullable=False, server_default="pending"
        ),
        sa.Column(
            "is_assumption", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("duplicate_of", sa.String(36)),
        *_timestamps(),
    )
    op.create_index("ix_threat_run_id", "threat", ["run_id"])
    op.create_index("ix_threat_component_ref", "threat", ["component_ref"])
    op.create_index("ix_threat_run_review", "threat", ["run_id", "review_status"])
    op.create_index("ix_threat_run_stride", "threat", ["run_id", "stride"])

    op.create_table(
        "kb_chunk",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(40), nullable=False),
        sa.Column("identifier", sa.String(80), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("lang", sa.String(5), nullable=False, server_default="tr"),
        sa.Column("license", sa.String(200)),
        sa.Column("url", sa.String(600)),
        sa.Column("verification", sa.String(20)),
        sa.Column("tags", postgresql.JSONB()),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column("search_vector", postgresql.TSVECTOR()),
        *_timestamps(),
        sa.UniqueConstraint("source", "identifier", "lang", name="uq_kb_source_ident"),
    )
    op.create_index("ix_kb_chunk_source", "kb_chunk", ["source"])
    op.create_index("ix_kb_chunk_identifier", "kb_chunk", ["identifier"])
    op.create_index(
        "ix_kb_search_vector", "kb_chunk", ["search_vector"], postgresql_using="gin"
    )

    op.create_table(
        "llm_call",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(36),
            sa.ForeignKey("analysis_run.id", ondelete="CASCADE"),
        ),
        sa.Column("step_no", sa.Integer()),
        sa.Column("provider", sa.String(40), nullable=False),
        sa.Column("model", sa.String(120)),
        sa.Column("prompt_hash", sa.String(64), nullable=False),
        sa.Column("prompt_name", sa.String(120)),
        sa.Column("request_payload", postgresql.JSONB()),
        sa.Column("response_payload", postgresql.JSONB()),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("prompt_tokens", sa.Integer()),
        sa.Column("completion_tokens", sa.Integer()),
        sa.Column(
            "from_cache", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("repair_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ok"),
        sa.Column("error_message", sa.Text()),
        *_timestamps(),
    )
    op.create_index("ix_llm_call_run_id", "llm_call", ["run_id"])
    op.create_index("ix_llm_call_prompt_hash", "llm_call", ["prompt_hash"])

    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("at", _TS, nullable=False),
        sa.Column("actor", sa.String(120), nullable=False),
        sa.Column("actor_role", sa.String(40), nullable=False),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("object_type", sa.String(60), nullable=False),
        sa.Column("object_id", sa.String(36)),
        sa.Column("run_id", sa.String(36)),
        sa.Column("old_value", postgresql.JSONB()),
        sa.Column("new_value", postgresql.JSONB()),
        sa.Column("reason", sa.Text()),
    )
    op.create_index("ix_audit_log_at", "audit_log", ["at"])
    op.create_index("ix_audit_log_object_id", "audit_log", ["object_id"])
    op.create_index("ix_audit_log_run_id", "audit_log", ["run_id"])


def downgrade() -> None:
    op.drop_table("audit_log")
    op.drop_table("llm_call")
    op.drop_table("kb_chunk")
    op.drop_table("threat")
    op.drop_table("system_model")
    op.drop_table("run_step")
    op.drop_table("analysis_run")
    op.drop_table("document")
    op.drop_table("project")
