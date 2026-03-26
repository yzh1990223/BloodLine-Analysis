"""Query helpers for scan, job, and table lineage APIs."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from bloodline_api.models import Edge, Node, ScanRun


class LineageQueryService:
    """Small read-side service for the API routes."""

    def search_tables(self, db: Session, query: str = "") -> list[Node]:
        stmt = select(Node).where(Node.type == "table")
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where((Node.key.ilike(pattern)) | (Node.name.ilike(pattern)))
        stmt = stmt.order_by(Node.name.asc(), Node.id.asc())
        return list(db.scalars(stmt).all())

    def list_scan_runs(self, db: Session) -> list[ScanRun]:
        stmt = select(ScanRun).order_by(ScanRun.created_at.desc(), ScanRun.id.desc())
        return list(db.scalars(stmt).all())

    def get_table_lineage(self, db: Session, table_key: str) -> dict[str, Any] | None:
        table = db.scalar(select(Node).where(Node.type == "table", Node.key == table_key))
        if table is None:
            return None

        upstream_stmt = (
            select(Node)
            .join(Edge, Edge.src_node_id == Node.id)
            .where(Edge.type == "FLOWS_TO", Edge.dst_node_id == table.id)
            .order_by(Node.name.asc(), Node.id.asc())
        )
        downstream_stmt = (
            select(Node)
            .join(Edge, Edge.dst_node_id == Node.id)
            .where(Edge.type == "FLOWS_TO", Edge.src_node_id == table.id)
            .order_by(Node.name.asc(), Node.id.asc())
        )
        upstream_tables = list(db.scalars(upstream_stmt).all())
        downstream_tables = list(db.scalars(downstream_stmt).all())

        return {
            "table": {"id": table.id, "key": table.key, "name": table.name},
            "upstream_tables": [
                {"id": node.id, "key": node.key, "name": node.name} for node in upstream_tables
            ],
            "downstream_tables": [
                {"id": node.id, "key": node.key, "name": node.name} for node in downstream_tables
            ],
        }


lineage_query_service = LineageQueryService()
