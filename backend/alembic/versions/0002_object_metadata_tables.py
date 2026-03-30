"""Add object metadata tables for latest MySQL metadata snapshots."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_object_metadata_tables"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "object_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("node_id", sa.Integer(), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("database_name", sa.String(length=255), nullable=False),
        sa.Column("object_name", sa.String(length=255), nullable=False),
        sa.Column("object_kind", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.String(length=1024), nullable=True),
        sa.Column("metadata_source", sa.String(length=64), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_object_metadata_node_id", "object_metadata", ["node_id"], unique=True)
    op.create_index("ix_object_metadata_database_name", "object_metadata", ["database_name"])
    op.create_index("ix_object_metadata_object_kind", "object_metadata", ["object_kind"])

    op.create_table(
        "object_metadata_columns",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("metadata_id", sa.Integer(), sa.ForeignKey("object_metadata.id"), nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=False),
        sa.Column("data_type", sa.String(length=255), nullable=False),
        sa.Column("ordinal_position", sa.Integer(), nullable=False),
        sa.Column("is_nullable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("column_comment", sa.String(length=1024), nullable=True),
        sa.UniqueConstraint(
            "metadata_id",
            "column_name",
            name="uq_object_metadata_columns_metadata_id_column_name",
        ),
    )
    op.create_index("ix_object_metadata_columns_metadata_id", "object_metadata_columns", ["metadata_id"])


def downgrade() -> None:
    op.drop_index("ix_object_metadata_columns_metadata_id", table_name="object_metadata_columns")
    op.drop_table("object_metadata_columns")

    op.drop_index("ix_object_metadata_object_kind", table_name="object_metadata")
    op.drop_index("ix_object_metadata_database_name", table_name="object_metadata")
    op.drop_index("ix_object_metadata_node_id", table_name="object_metadata")
    op.drop_table("object_metadata")
