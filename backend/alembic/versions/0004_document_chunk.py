"""Index uploaded documents for retrieval.

A long architecture document cannot be handed to the model whole, and
cutting it at a fixed length silently drops the end - usually the
operations and security sections. Chunking it here lets step 3 fetch the
passages that are actually about the component being analysed.

Revision ID: 0004_document_chunk
Revises: 0003_step_output
Create Date: 2026-11-24
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision = "0004_document_chunk"
down_revision = "0003_step_output"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    op.create_table(
        "document_chunk",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("document.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("page", sa.Integer()),
        sa.Column("section", sa.String(300)),
        sa.Column("ordinal", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM)),
        sa.Column("search_vector", postgresql.TSVECTOR()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_document_chunk_document", "document_chunk", ["document_id"])
    op.create_index(
        "ix_document_chunk_search",
        "document_chunk",
        ["search_vector"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunk_search", table_name="document_chunk")
    op.drop_index("ix_document_chunk_document", table_name="document_chunk")
    op.drop_table("document_chunk")
