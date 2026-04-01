"""add view definition metadata fields

Revision ID: 0004_view_definition_metadata
Revises: 0003_scan_run_inputs
Create Date: 2026-04-01
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0004_view_definition_metadata"
down_revision = "0003_scan_run_inputs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("object_metadata")}

    if "view_definition" not in existing_columns:
        op.add_column("object_metadata", sa.Column("view_definition", sa.String(), nullable=True))
    if "view_parse_status" not in existing_columns:
        op.add_column(
            "object_metadata",
            sa.Column("view_parse_status", sa.String(length=32), nullable=False, server_default="not_applicable"),
        )
    if "view_parse_error" not in existing_columns:
        op.add_column("object_metadata", sa.Column("view_parse_error", sa.String(length=2048), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_columns = {column["name"] for column in inspector.get_columns("object_metadata")}

    if "view_parse_error" in existing_columns:
        op.drop_column("object_metadata", "view_parse_error")
    if "view_parse_status" in existing_columns:
        op.drop_column("object_metadata", "view_parse_status")
    if "view_definition" in existing_columns:
        op.drop_column("object_metadata", "view_definition")
