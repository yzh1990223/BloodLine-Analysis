"""Persist latest scan input payloads on scan runs."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_scan_run_inputs"
down_revision = "0002_object_metadata_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "scan_runs",
        sa.Column("inputs", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )


def downgrade() -> None:
    op.drop_column("scan_runs", "inputs")
