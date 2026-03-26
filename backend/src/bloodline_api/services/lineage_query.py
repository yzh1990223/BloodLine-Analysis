"""Query helpers for scan, job, and table lineage APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from bloodline_api.models import Edge, Node, ScanRun
from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.repo_parser import RepoParser
from bloodline_api.services.graph_builder import build_table_flows

BACKEND_ROOT = Path(__file__).resolve().parents[3]


def _resolve_input_path(value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else BACKEND_ROOT / path


def _node_payload(node_type: str, source: str | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"source": source or node_type}
    return payload


class LineageQueryService:
    """Small read-side service for the API routes."""

    def _get_or_create_node(self, db: Session, node_type: str, key: str, name: str) -> Node:
        node = db.scalar(select(Node).where(Node.key == key))
        if node is not None:
            return node

        node = Node(type=node_type, key=key, name=name, payload=_node_payload(node_type))
        db.add(node)
        db.flush()
        return node

    def _ensure_edge(
        self,
        db: Session,
        edge_type: str,
        src_node_id: int,
        dst_node_id: int,
        *,
        is_derived: bool = False,
        payload: dict[str, Any] | None = None,
    ) -> Edge:
        edge = db.scalar(
            select(Edge).where(
                Edge.type == edge_type,
                Edge.src_node_id == src_node_id,
                Edge.dst_node_id == dst_node_id,
                Edge.is_derived == is_derived,
            )
        )
        if edge is not None:
            return edge

        edge = Edge(
            type=edge_type,
            src_node_id=src_node_id,
            dst_node_id=dst_node_id,
            is_derived=is_derived,
            payload=payload or {},
        )
        db.add(edge)
        db.flush()
        return edge

    def _related_objects(self, db: Session, table: Node) -> dict[str, list[dict[str, Any]]]:
        transformation_nodes: dict[str, Node] = {}
        job_nodes: dict[str, Node] = {}
        java_module_nodes: dict[str, Node] = {}

        actor_edges = db.scalars(
            select(Edge).where(
                Edge.dst_node_id == table.id,
                Edge.type.in_(("READS", "WRITES")),
            )
        ).all()

        for edge in actor_edges:
            actor = db.get(Node, edge.src_node_id)
            if actor is None:
                continue
            if actor.type == "transformation":
                transformation_nodes[actor.key] = actor
                job_rows = db.scalars(
                    select(Node)
                    .join(Edge, Edge.src_node_id == Node.id)
                    .where(Edge.type == "CALLS", Edge.dst_node_id == actor.id)
                ).all()
                for job in job_rows:
                    if job.type == "job":
                        job_nodes[job.key] = job
            elif actor.type == "java_module":
                java_module_nodes[actor.key] = actor

        return {
            "jobs": [
                {"id": node.id, "key": node.key, "name": node.name}
                for node in sorted(job_nodes.values(), key=lambda item: (item.name, item.id))
            ],
            "java_modules": [
                {"id": node.id, "key": node.key, "name": node.name}
                for node in sorted(java_module_nodes.values(), key=lambda item: (item.name, item.id))
            ],
            "transformations": [
                {"id": node.id, "key": node.key, "name": node.name}
                for node in sorted(transformation_nodes.values(), key=lambda item: (item.name, item.id))
            ],
        }

    def scan_from_inputs(
        self,
        db: Session,
        *,
        repo_path: str | None = None,
        java_source_root: str | None = None,
        mysql_dsn: str | None = None,
    ) -> ScanRun:
        _ = mysql_dsn
        now = datetime.now(timezone.utc)
        scan_run = ScanRun(status="running", started_at=now)
        db.add(scan_run)
        db.flush()

        fact_edges: list[tuple[str, str, str]] = []
        table_nodes: dict[str, Node] = {}

        if repo_path:
            repo_result = RepoParser().parse_file(_resolve_input_path(repo_path))
            job_nodes = {
                job.name: self._get_or_create_node(db, "job", f"job:{job.name}", job.name)
                for job in repo_result.jobs
            }
            transformation_nodes = {
                transformation.name: self._get_or_create_node(
                    db, "transformation", f"transformation:{transformation.name}", transformation.name
                )
                for transformation in repo_result.transformations
            }

            for call in repo_result.job_transformation_calls:
                job_node = job_nodes.get(call.job_name)
                transformation_node = transformation_nodes.get(call.transformation_name)
                if job_node is None or transformation_node is None:
                    continue
                self._ensure_edge(db, "CALLS", job_node.id, transformation_node.id)

            for step_key, table_names in repo_result.step_reads.items():
                transformation_name = step_key.split("::", 1)[0]
                transformation_node = transformation_nodes.get(transformation_name)
                if transformation_node is None:
                    continue
                for table_name in table_names:
                    table_node = table_nodes.get(table_name)
                    if table_node is None:
                        table_node = self._get_or_create_node(
                            db, "table", f"table:{table_name}", table_name
                        )
                        table_nodes[table_name] = table_node
                    self._ensure_edge(
                        db,
                        "READS",
                        transformation_node.id,
                        table_node.id,
                        payload={"step": step_key, "source": "repo"},
                    )
                    fact_edges.append(
                        ("READS", transformation_node.key, table_node.key)
                    )

            for step_key, table_names in repo_result.step_writes.items():
                transformation_name = step_key.split("::", 1)[0]
                transformation_node = transformation_nodes.get(transformation_name)
                if transformation_node is None:
                    continue
                for table_name in table_names:
                    table_node = table_nodes.get(table_name)
                    if table_node is None:
                        table_node = self._get_or_create_node(
                            db, "table", f"table:{table_name}", table_name
                        )
                        table_nodes[table_name] = table_node
                    self._ensure_edge(
                        db,
                        "WRITES",
                        transformation_node.id,
                        table_node.id,
                        payload={"step": step_key, "source": "repo"},
                    )
                    fact_edges.append(
                        ("WRITES", transformation_node.key, table_node.key)
                    )

        if java_source_root:
            java_root = _resolve_input_path(java_source_root)
            if java_root.is_dir():
                for java_file in sorted(java_root.rglob("*.java")):
                    java_result = JavaSqlParser().parse_file(java_file)
                    java_node = self._get_or_create_node(
                        db,
                        "java_module",
                        f"java_module:{java_result.module_name}",
                        java_result.module_name,
                    )
                    for table_name in java_result.read_tables:
                        table_node = table_nodes.get(table_name)
                        if table_node is None:
                            table_node = self._get_or_create_node(
                                db, "table", f"table:{table_name}", table_name
                            )
                            table_nodes[table_name] = table_node
                        self._ensure_edge(db, "READS", java_node.id, table_node.id)
                        fact_edges.append(("READS", java_node.key, table_node.key))
                    for table_name in java_result.write_tables:
                        table_node = table_nodes.get(table_name)
                        if table_node is None:
                            table_node = self._get_or_create_node(
                                db, "table", f"table:{table_name}", table_name
                            )
                            table_nodes[table_name] = table_node
                        self._ensure_edge(db, "WRITES", java_node.id, table_node.id)
                        fact_edges.append(("WRITES", java_node.key, table_node.key))

        table_flows = build_table_flows(fact_edges)
        for source_key, target_key in table_flows:
            source_table = table_nodes.get(source_key.split("table:", 1)[1])
            target_table = table_nodes.get(target_key.split("table:", 1)[1])
            if source_table is None or target_table is None:
                continue
            self._ensure_edge(db, "FLOWS_TO", source_table.id, target_table.id, is_derived=True)

        scan_run.status = "completed"
        scan_run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan_run)
        return scan_run

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

    def list_jobs(self, db: Session) -> list[Node]:
        stmt = select(Node).where(Node.type == "job").order_by(Node.name.asc(), Node.id.asc())
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
            "related_objects": self._related_objects(db, table),
        }

    def get_table_impact(self, db: Session, table_key: str) -> dict[str, Any] | None:
        lineage = self.get_table_lineage(db, table_key)
        if lineage is None:
            return None
        lineage["impacted_tables"] = lineage["downstream_tables"]
        return lineage


lineage_query_service = LineageQueryService()
