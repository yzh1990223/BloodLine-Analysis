"""Initial schema for scan runs, nodes, and edges."""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scan_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_scan_runs_status", "scan_runs", ["status"])

    op.create_table(
        "nodes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_nodes_type", "nodes", ["type"])
    op.create_index("ix_nodes_key", "nodes", ["key"], unique=True)

    op.create_table(
        "edges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column("src_node_id", sa.Integer(), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("dst_node_id", sa.Integer(), sa.ForeignKey("nodes.id"), nullable=False),
        sa.Column("is_derived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_edges_type", "edges", ["type"])
    op.create_index("ix_edges_src_node_id", "edges", ["src_node_id"])
    op.create_index("ix_edges_dst_node_id", "edges", ["dst_node_id"])


def downgrade() -> None:
    op.drop_index("ix_edges_dst_node_id", table_name="edges")
    op.drop_index("ix_edges_src_node_id", table_name="edges")
    op.drop_index("ix_edges_type", table_name="edges")
    op.drop_table("edges")

    op.drop_index("ix_nodes_key", table_name="nodes")
    op.drop_index("ix_nodes_type", table_name="nodes")
    op.drop_table("nodes")

    op.drop_index("ix_scan_runs_status", table_name="scan_runs")
    op.drop_table("scan_runs")
