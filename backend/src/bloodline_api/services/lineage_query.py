"""Query helpers for scan, job, and table lineage APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from bloodline_api.models import Edge, Node, ScanRun
from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.repo_parser import RepoParser
from bloodline_api.services.graph_builder import build_table_flows

BACKEND_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_OBJECT_TYPE = "data_table"


def _resolve_input_path(value: str) -> Path:
    """Resolve relative scan inputs against the backend workspace."""

    path = Path(value)
    return path if path.is_absolute() else BACKEND_ROOT / path


def _node_payload(
    node_type: str,
    source: str | None = None,
    *,
    object_type: str | None = None,
) -> dict[str, Any]:
    """Build the minimal payload stored on graph nodes in the MVP."""

    payload: dict[str, Any] = {"source": source or node_type}
    if object_type is not None:
        payload["object_type"] = object_type
    return payload


def _object_key(object_type: str, name: str) -> str:
    """Build stable keys for lineage objects while keeping data-table keys backward-compatible."""

    if object_type == "data_table":
        return f"table:{name}"
    if object_type == "table_view":
        return f"view:{name}"
    return f"{object_type}:{name}"


def _serialize_object(node: Node) -> dict[str, Any]:
    """Serialize one lineage object with its frontend-visible type label."""

    return {
        "id": node.id,
        "key": node.key,
        "name": node.name,
        "object_type": node.payload.get("object_type", DEFAULT_OBJECT_TYPE),
    }


class LineageQueryService:
    """Orchestrate scan persistence and graph-shaped query responses."""

    def reset_graph_state(self, db: Session) -> None:
        """Clear persisted graph entities before a full rescan rebuild."""

        db.execute(delete(Edge))
        db.execute(delete(Node))
        db.flush()

    def _get_or_create_node(self, db: Session, node_type: str, key: str, name: str) -> Node:
        """Upsert a graph node by stable business key."""

        node = db.scalar(select(Node).where(Node.key == key))
        if node is not None:
            return node

        node = Node(type=node_type, key=key, name=name, payload=_node_payload(node_type))
        db.add(node)
        db.flush()
        return node

    def _get_or_create_object_node(self, db: Session, *, name: str, object_type: str) -> Node:
        """Upsert a lineage object node such as a data table, source table, or source file."""

        key = _object_key(object_type, name)
        node = db.scalar(select(Node).where(Node.key == key))
        if node is not None:
            payload = dict(node.payload or {})
            if payload.get("object_type") != object_type:
                payload["object_type"] = object_type
                node.payload = payload
                db.flush()
            return node

        node = Node(
            type="data_object",
            key=key,
            name=name,
            payload=_node_payload("data_object", source="repo", object_type=object_type),
        )
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
        """Ensure a unique edge exists for a given source/target/type tuple."""

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

    def _collect_actor_table_keys(self, db: Session, actor: Node) -> list[str]:
        """Collect stable object keys touched by one job, transformation, or Java module."""

        table_keys: set[str] = set()

        if actor.type in {"job", "transformation", "java_module"}:
            direct_table_ids = db.scalars(
                select(Edge.dst_node_id).where(
                    Edge.src_node_id == actor.id,
                    Edge.type.in_(("READS", "WRITES")),
                )
            ).all()
            for node_id in direct_table_ids:
                table = db.get(Node, node_id)
                if table is not None and table.type in {"table", "data_object"}:
                    table_keys.add(table.key)

        if actor.type == "job":
            transformation_ids = db.scalars(
                select(Edge.dst_node_id).where(Edge.src_node_id == actor.id, Edge.type == "CALLS")
            ).all()
            for transformation_id in transformation_ids:
                touched_table_ids = db.scalars(
                    select(Edge.dst_node_id).where(
                        Edge.src_node_id == transformation_id,
                        Edge.type.in_(("READS", "WRITES")),
                    )
                ).all()
                for node_id in touched_table_ids:
                    table = db.get(Node, node_id)
                    if table is not None and table.type in {"table", "data_object"}:
                        table_keys.add(table.key)

        return sorted(table_keys)

    def _related_objects(self, db: Session, table: Node) -> dict[str, list[dict[str, Any]]]:
        """Collect jobs, Java modules, and transformations linked to one table."""

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
            elif actor.type == "job":
                job_nodes[actor.key] = actor
            elif actor.type == "java_module":
                java_module_nodes[actor.key] = actor

        return {
            "jobs": [
                {
                    "id": node.id,
                    "key": node.key,
                    "name": node.name,
                    "related_table_keys": self._collect_actor_table_keys(db, node),
                }
                for node in sorted(job_nodes.values(), key=lambda item: (item.name, item.id))
            ],
            "java_modules": [
                {
                    "id": node.id,
                    "key": node.key,
                    "name": node.name,
                    "related_table_keys": self._collect_actor_table_keys(db, node),
                }
                for node in sorted(java_module_nodes.values(), key=lambda item: (item.name, item.id))
            ],
            "transformations": [
                {
                    "id": node.id,
                    "key": node.key,
                    "name": node.name,
                    "related_table_keys": self._collect_actor_table_keys(db, node),
                }
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
        """Run the MVP scan pipeline and persist the resulting graph state."""

        _ = mysql_dsn
        self.reset_graph_state(db)
        now = datetime.now(timezone.utc)
        scan_run = ScanRun(status="running", started_at=now)
        db.add(scan_run)
        db.flush()

        fact_edges: list[tuple[str, str, str]] = []
        object_nodes: dict[str, Node] = {}

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
                for object_ref in table_names:
                    table_node = object_nodes.get(_object_key(object_ref.object_type, object_ref.name))
                    if table_node is None:
                        table_node = self._get_or_create_object_node(
                            db,
                            name=object_ref.name,
                            object_type=object_ref.object_type,
                        )
                        object_nodes[table_node.key] = table_node
                    self._ensure_edge(
                        db,
                        "READS",
                        transformation_node.id,
                        table_node.id,
                        payload={"step": step_key, "source": "repo"},
                    )
                    fact_edges.append(("READS", step_key, table_node.key))

            for step_key, table_names in repo_result.step_writes.items():
                transformation_name = step_key.split("::", 1)[0]
                transformation_node = transformation_nodes.get(transformation_name)
                if transformation_node is None:
                    continue
                for object_ref in table_names:
                    table_node = object_nodes.get(_object_key(object_ref.object_type, object_ref.name))
                    if table_node is None:
                        table_node = self._get_or_create_object_node(
                            db,
                            name=object_ref.name,
                            object_type=object_ref.object_type,
                        )
                        object_nodes[table_node.key] = table_node
                    self._ensure_edge(
                        db,
                        "WRITES",
                        transformation_node.id,
                        table_node.id,
                        payload={"step": step_key, "source": "repo"},
                    )
                    fact_edges.append(("WRITES", step_key, table_node.key))

            for entry_key, object_refs in repo_result.job_reads.items():
                job_name = entry_key.split("::", 1)[0]
                job_node = job_nodes.get(job_name)
                if job_node is None:
                    continue
                for object_ref in object_refs:
                    table_node = object_nodes.get(_object_key(object_ref.object_type, object_ref.name))
                    if table_node is None:
                        table_node = self._get_or_create_object_node(
                            db,
                            name=object_ref.name,
                            object_type=object_ref.object_type,
                        )
                        object_nodes[table_node.key] = table_node
                    self._ensure_edge(
                        db,
                        "READS",
                        job_node.id,
                        table_node.id,
                        payload={"entry": entry_key, "source": "repo"},
                    )
                    fact_edges.append(("READS", entry_key, table_node.key))

            for entry_key, object_refs in repo_result.job_writes.items():
                job_name = entry_key.split("::", 1)[0]
                job_node = job_nodes.get(job_name)
                if job_node is None:
                    continue
                for object_ref in object_refs:
                    table_node = object_nodes.get(_object_key(object_ref.object_type, object_ref.name))
                    if table_node is None:
                        table_node = self._get_or_create_object_node(
                            db,
                            name=object_ref.name,
                            object_type=object_ref.object_type,
                        )
                        object_nodes[table_node.key] = table_node
                    self._ensure_edge(
                        db,
                        "WRITES",
                        job_node.id,
                        table_node.id,
                        payload={"entry": entry_key, "source": "repo"},
                    )
                    fact_edges.append(("WRITES", entry_key, table_node.key))

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
                        object_key = _object_key("data_table", table_name)
                        table_node = object_nodes.get(object_key)
                        if table_node is None:
                            table_node = self._get_or_create_object_node(
                                db, name=table_name, object_type="data_table"
                            )
                            object_nodes[table_node.key] = table_node
                        self._ensure_edge(db, "READS", java_node.id, table_node.id)
                    for table_name in java_result.write_tables:
                        object_key = _object_key("data_table", table_name)
                        table_node = object_nodes.get(object_key)
                        if table_node is None:
                            table_node = self._get_or_create_object_node(
                                db, name=table_name, object_type="data_table"
                            )
                            object_nodes[table_node.key] = table_node
                        self._ensure_edge(db, "WRITES", java_node.id, table_node.id)
                    # Preserve statement boundaries so unrelated SQL literals in one class
                    # do not collapse into false direct table-to-table flows.
                    for statement in java_result.statements:
                        statement_actor = f"{java_node.key}#{statement.statement_id}"
                        for table_name in statement.read_tables:
                            table_node = object_nodes[_object_key("data_table", table_name)]
                            fact_edges.append(("READS", statement_actor, table_node.key))
                        for table_name in statement.write_tables:
                            table_node = object_nodes[_object_key("data_table", table_name)]
                            fact_edges.append(("WRITES", statement_actor, table_node.key))

        table_flows = build_table_flows(fact_edges)
        for source_key, target_key in table_flows:
            source_table = object_nodes.get(source_key)
            target_table = object_nodes.get(target_key)
            if source_table is None or target_table is None:
                continue
            self._ensure_edge(db, "FLOWS_TO", source_table.id, target_table.id, is_derived=True)

        scan_run.status = "completed"
        scan_run.finished_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(scan_run)
        return scan_run

    def search_tables(self, db: Session, query: str = "") -> list[Node]:
        """Search table nodes by key or name for the frontend search page."""

        stmt = select(Node).where(Node.type.in_(("table", "data_object")))
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where((Node.key.ilike(pattern)) | (Node.name.ilike(pattern)))
        stmt = stmt.order_by(Node.name.asc(), Node.id.asc())
        return list(db.scalars(stmt).all())

    def list_scan_runs(self, db: Session) -> list[ScanRun]:
        """Return scan runs in reverse chronological order."""

        stmt = select(ScanRun).order_by(ScanRun.created_at.desc(), ScanRun.id.desc())
        return list(db.scalars(stmt).all())

    def list_jobs(self, db: Session) -> list[Node]:
        """Return scanned job nodes for list views and related-object lookups."""

        stmt = select(Node).where(Node.type == "job").order_by(Node.name.asc(), Node.id.asc())
        return list(db.scalars(stmt).all())

    def get_table_lineage(self, db: Session, table_key: str) -> dict[str, Any] | None:
        """Return one table with its direct upstream/downstream neighbors."""

        table = db.scalar(select(Node).where(Node.type.in_(("table", "data_object")), Node.key == table_key))
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
            "table": _serialize_object(table),
            "upstream_tables": [_serialize_object(node) for node in upstream_tables],
            "downstream_tables": [_serialize_object(node) for node in downstream_tables],
            "related_objects": self._related_objects(db, table),
        }

    def get_table_impact(self, db: Session, table_key: str) -> dict[str, Any] | None:
        """Extend direct lineage with downstream impact expansion."""

        lineage = self.get_table_lineage(db, table_key)
        if lineage is None:
            return None
        table = db.scalar(select(Node).where(Node.type.in_(("table", "data_object")), Node.key == table_key))
        if table is None:
            return None

        impacted_tables = self._collect_downstream_tables(db, table.id, max_hops=3)
        lineage["impacted_tables"] = impacted_tables
        return lineage

    def _collect_downstream_tables(
        self, db: Session, start_table_id: int, *, max_hops: int = 3
    ) -> list[dict[str, Any]]:
        """Traverse downstream table flows breadth-first up to a hop limit."""

        frontier = {start_table_id}
        seen = {start_table_id}
        impacted: list[dict[str, Any]] = []

        for hop in range(1, max_hops + 1):
            if not frontier:
                break

            next_ids = db.scalars(
                select(Edge.dst_node_id).where(
                    Edge.type == "FLOWS_TO",
                    Edge.src_node_id.in_(frontier),
                )
            ).all()
            next_frontier: set[int] = set()
            for node_id in next_ids:
                if node_id in seen:
                    continue
                seen.add(node_id)
                next_frontier.add(node_id)
                node = db.get(Node, node_id)
                if node is not None and node.type in {"table", "data_object"}:
                    impacted.append(
                        {
                            "id": node.id,
                            "key": node.key,
                            "name": node.name,
                            "object_type": node.payload.get("object_type", DEFAULT_OBJECT_TYPE),
                            "hop": hop,
                        }
                    )
            frontier = next_frontier

        return impacted

    def get_job_detail(self, db: Session, job_key: str) -> dict[str, Any] | None:
        """Return one job together with its called transformations and touched tables."""

        job = db.scalar(select(Node).where(Node.type == "job", Node.key == job_key))
        if job is None:
            return None

        transformation_rows = db.scalars(
            select(Node)
            .join(Edge, Edge.dst_node_id == Node.id)
            .where(Edge.type == "CALLS", Edge.src_node_id == job.id)
            .order_by(Node.name.asc(), Node.id.asc())
        ).all()

        table_ids: set[int] = set()
        for transformation in transformation_rows:
            table_ids.update(
                db.scalars(
                    select(Edge.dst_node_id).where(
                        Edge.src_node_id == transformation.id,
                        Edge.type.in_(("READS", "WRITES")),
                    )
                ).all()
            )

        table_rows = []
        if table_ids:
            table_rows = list(
                db.scalars(
                    select(Node)
                    .where(Node.id.in_(table_ids))
                    .order_by(Node.name.asc(), Node.id.asc())
                ).all()
            )

        return {
            "id": job.id,
            "key": job.key,
            "name": job.name,
            "transformations": [
                {"id": node.id, "key": node.key, "name": node.name} for node in transformation_rows
            ],
            "tables": [{"id": node.id, "key": node.key, "name": node.name} for node in table_rows],
        }

    def get_java_module_detail(self, db: Session, module_key: str) -> dict[str, Any] | None:
        """Return one Java module together with its read/write table sets."""

        module = db.scalar(select(Node).where(Node.type == "java_module", Node.key == module_key))
        if module is None:
            return None

        read_ids = db.scalars(
            select(Edge.dst_node_id).where(Edge.type == "READS", Edge.src_node_id == module.id)
        ).all()
        write_ids = db.scalars(
            select(Edge.dst_node_id).where(Edge.type == "WRITES", Edge.src_node_id == module.id)
        ).all()

        read_tables = []
        if read_ids:
            read_tables = list(
                db.scalars(
                    select(Node)
                    .where(Node.id.in_(read_ids))
                    .order_by(Node.name.asc(), Node.id.asc())
                ).all()
            )
        write_tables = []
        if write_ids:
            write_tables = list(
                db.scalars(
                    select(Node)
                    .where(Node.id.in_(write_ids))
                    .order_by(Node.name.asc(), Node.id.asc())
                ).all()
            )

        return {
            "id": module.id,
            "key": module.key,
            "name": module.name,
            "read_tables": [
                {"id": node.id, "key": node.key, "name": node.name} for node in read_tables
            ],
            "write_tables": [
                {"id": node.id, "key": node.key, "name": node.name} for node in write_tables
            ],
        }


lineage_query_service = LineageQueryService()
