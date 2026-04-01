"""add scan failure records

Revision ID: 0005_scan_failures
Revises: 0004_view_definition_metadata
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0005_scan_failures"
down_revision = "0004_view_definition_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "scan_failures" in existing_tables:
        return

    op.create_table(
        "scan_failures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scan_run_id", sa.Integer(), sa.ForeignKey("scan_runs.id"), nullable=False),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("file_path", sa.String(length=1024), nullable=False),
        sa.Column("failure_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.String(length=2048), nullable=False),
        sa.Column("object_key", sa.String(length=255), nullable=True),
        sa.Column("sql_snippet", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scan_failures_scan_run_id", "scan_failures", ["scan_run_id"])
    op.create_index("ix_scan_failures_source_type", "scan_failures", ["source_type"])
    op.create_index("ix_scan_failures_file_path", "scan_failures", ["file_path"])
    op.create_index("ix_scan_failures_failure_type", "scan_failures", ["failure_type"])
    op.create_index("ix_scan_failures_object_key", "scan_failures", ["object_key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "scan_failures" not in existing_tables:
        return

    op.drop_index("ix_scan_failures_object_key", table_name="scan_failures")
    op.drop_index("ix_scan_failures_failure_type", table_name="scan_failures")
    op.drop_index("ix_scan_failures_file_path", table_name="scan_failures")
    op.drop_index("ix_scan_failures_source_type", table_name="scan_failures")
    op.drop_index("ix_scan_failures_scan_run_id", table_name="scan_failures")
    op.drop_table("scan_failures")
