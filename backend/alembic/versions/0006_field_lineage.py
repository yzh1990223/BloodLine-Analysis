"""add field-level lineage table

Revision ID: 0006_field_lineage
Revises: 0005_scan_failures
Create Date: 2026-04-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0006_field_lineage"
down_revision = "0005_scan_failures"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "field_edges" in existing_tables:
        return

    op.create_table(
        "field_edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("edge_id", sa.Integer(), sa.ForeignKey("edges.id", ondelete="CASCADE"), nullable=True),
        sa.Column("src_node_id", sa.Integer(), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("dst_node_id", sa.Integer(), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("src_field", sa.String(length=255), nullable=False),
        sa.Column("dst_field", sa.String(length=255), nullable=False),
        sa.Column("is_derived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_field_edges_src_node_id", "field_edges", ["src_node_id"])
    op.create_index("ix_field_edges_dst_node_id", "field_edges", ["dst_node_id"])
    op.create_index("ix_field_edges_src_field", "field_edges", ["src_field"])
    op.create_index("ix_field_edges_dst_field", "field_edges", ["dst_field"])
    op.create_index("ix_field_edges_edge_id", "field_edges", ["edge_id"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = set(inspector.get_table_names())
    if "field_edges" not in existing_tables:
        return

    op.drop_index("ix_field_edges_edge_id", table_name="field_edges")
    op.drop_index("ix_field_edges_dst_field", table_name="field_edges")
    op.drop_index("ix_field_edges_src_field", table_name="field_edges")
    op.drop_index("ix_field_edges_dst_node_id", table_name="field_edges")
    op.drop_index("ix_field_edges_src_node_id", table_name="field_edges")
    op.drop_table("field_edges")
