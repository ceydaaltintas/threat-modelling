"""Give each pipeline step somewhere to keep its panel output.

Step 3 stores the knowledge it retrieved per component, step 4 its merge
statistics, and so on. Keeping it on the step row means a page reload shows
the same panel without re-running anything.

Revision ID: 0003_step_output
Revises: 0002_storage_path
Create Date: 2026-11-21
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_step_output"
down_revision = "0002_storage_path"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("run_step", sa.Column("output", postgresql.JSONB()))


def downgrade() -> None:
    op.drop_column("run_step", "output")
