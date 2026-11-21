"""Keep the uploaded file path on the document row.

Step 1 reads the file from disk, so the pipeline must know where it was
stored.

Revision ID: 0002_storage_path
Revises: 0001_initial
Create Date: 2026-11-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_storage_path"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("document", sa.Column("storage_path", sa.String(1000)))


def downgrade() -> None:
    op.drop_column("document", "storage_path")
