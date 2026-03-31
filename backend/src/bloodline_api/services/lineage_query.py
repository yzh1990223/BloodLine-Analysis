"""Query helpers for scan, job, and table lineage APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader
from bloodline_api.connectors.mysql_metadata import MySQLMetadataObject
from bloodline_api.connectors.mysql_metadata import build_mysql_metadata_request
from bloodline_api.models import Edge, Node, ObjectMetadata, ObjectMetadataColumn, ScanRun
from bloodline_api.parsers.java_controller_parser import parse_controller_endpoints
from bloodline_api.parsers.java_lineage_reducer import reduce_java_api_endpoints
from bloodline_api.parsers.java_lineage_reducer import reduce_java_modules
from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.repo_parser import RepoParser
from bloodline_api.services.graph_builder import build_table_flows

BACKEND_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_OBJECT_TYPE = "data_table"


def _resolve_input_path(value: str) -> Path:
    """Resolve relative scan inputs against the backend workspace."""

    normalized = value.strip().replace("\\ ", " ")
    path = Path(normalized)
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


def _normalize_object_name(name: str) -> str:
    """Normalize metadata-backed object names to lowercase dotted identifiers."""

    return name.strip().lower()


def _metadata_object_name(metadata_object: MySQLMetadataObject) -> str:
    """Build the fully qualified graph object name for one metadata object."""

    return _normalize_object_name(f"{metadata_object.database_name}.{metadata_object.object_name}")


def _metadata_object_type(metadata_object: MySQLMetadataObject) -> str:
    """Translate connector object kinds into graph-facing object types."""

    return "table_view" if metadata_object.object_kind == "view" else "data_table"


def _serialize_object(node: Node) -> dict[str, Any]:
    """Serialize one lineage object with its frontend-visible type label."""

    payload = {
        "id": node.id,
        "key": node.key,
        "name": node.name,
        "object_type": node.payload.get("object_type", DEFAULT_OBJECT_TYPE),
    }
    metadata = node.object_metadata
    if metadata is not None:
        payload["metadata"] = {
            "database_name": metadata.database_name,
            "object_name": metadata.object_name,
            "object_kind": metadata.object_kind,
            "comment": metadata.comment,
            "column_count": len(metadata.columns),
            "metadata_source": metadata.metadata_source,
        }
    return payload


class LineageQueryService:
    """Orchestrate scan persistence and graph-shaped query responses."""

    def reset_graph_state(self, db: Session) -> None:
        """Clear persisted graph entities before a full rescan rebuild."""

        db.execute(delete(ObjectMetadataColumn))
        db.execute(delete(ObjectMetadata))
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

    def _upsert_object_metadata(
        self,
        db: Session,
        *,
        node: Node,
        metadata_object: MySQLMetadataObject,
    ) -> None:
        """Persist the latest metadata snapshot for one table or view node."""

        metadata = node.object_metadata
        if metadata is None:
            metadata = ObjectMetadata(
                node=node,
                database_name=metadata_object.database_name,
                object_name=metadata_object.object_name,
                object_kind=metadata_object.object_kind,
                comment=metadata_object.comment,
                metadata_source="mysql_information_schema",
            )
            db.add(metadata)
            db.flush()
        else:
            metadata.database_name = metadata_object.database_name
            metadata.object_name = metadata_object.object_name
            metadata.object_kind = metadata_object.object_kind
            metadata.comment = metadata_object.comment
            metadata.metadata_source = "mysql_information_schema"

        metadata.columns[:] = [
            ObjectMetadataColumn(
                column_name=column.column_name,
                data_type=column.data_type,
                ordinal_position=column.ordinal_position,
                is_nullable=column.is_nullable,
                column_comment=column.column_comment,
            )
            for column in metadata_object.columns
        ]
        db.flush()

    def _load_mysql_metadata_nodes(
        self,
        db: Session,
        *,
        mysql_dsn: str | None,
        metadata_databases: list[str] | None,
        object_nodes: dict[str, Node],
    ) -> dict[str, Node]:
        """Load metadata-backed nodes and build alias lookups for conservative merges."""

        request = build_mysql_metadata_request(
            mysql_dsn=mysql_dsn,
            metadata_databases=metadata_databases,
        )
        if request is None:
            return {}

        metadata_objects = MySQLMetadataLoader().load(request)
        bare_name_candidates: dict[str, list[Node]] = {}
        alias_nodes: dict[str, Node] = {}

        for metadata_object in metadata_objects:
            object_name = _metadata_object_name(metadata_object)
            object_type = _metadata_object_type(metadata_object)
            node = self._get_or_create_object_node(db, name=object_name, object_type=object_type)
            object_nodes[node.key] = node
            alias_nodes[object_name] = node
            bare_name_candidates.setdefault(_normalize_object_name(metadata_object.object_name), []).append(node)
            self._upsert_object_metadata(db, node=node, metadata_object=metadata_object)

        for bare_name, nodes in bare_name_candidates.items():
            if len(nodes) == 1:
                alias_nodes[bare_name] = nodes[0]

        return alias_nodes

    def _resolve_object_node(
        self,
        db: Session,
        *,
        name: str,
        object_type: str,
        object_nodes: dict[str, Node],
        metadata_aliases: dict[str, Node],
    ) -> Node:
        """Resolve one lineage object, reusing metadata-backed nodes when safely possible."""

        normalized_name = _normalize_object_name(name)
        if object_type == "data_table":
            metadata_node = metadata_aliases.get(normalized_name)
            if metadata_node is not None:
                object_nodes[metadata_node.key] = metadata_node
                return metadata_node

        object_key = _object_key(object_type, normalized_name)
        table_node = object_nodes.get(object_key)
        if table_node is None:
            table_node = self._get_or_create_object_node(
                db,
                name=normalized_name,
                object_type=object_type,
            )
            object_nodes[table_node.key] = table_node
        return table_node

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

        if actor.type in {"job", "transformation", "java_module", "api_endpoint"}:
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
        api_endpoint_nodes: dict[str, Node] = {}

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
            elif actor.type == "api_endpoint":
                api_endpoint_nodes[actor.key] = actor

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
            "api_endpoints": [
                {
                    "id": node.id,
                    "key": node.key,
                    "name": node.name,
                    "related_table_keys": self._collect_actor_table_keys(db, node),
                }
                for node in sorted(api_endpoint_nodes.values(), key=lambda item: (item.name, item.id))
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
        metadata_databases: list[str] | None = None,
    ) -> ScanRun:
        """Run the MVP scan pipeline and persist the resulting graph state."""

        _ = mysql_dsn
        _ = metadata_databases
        self.reset_graph_state(db)
        now = datetime.now(timezone.utc)
        scan_run = ScanRun(status="running", started_at=now)
        db.add(scan_run)
        db.flush()

        fact_edges: list[tuple[str, str, str]] = []
        object_nodes: dict[str, Node] = {}
        metadata_aliases = self._load_mysql_metadata_nodes(
            db,
            mysql_dsn=mysql_dsn,
            metadata_databases=metadata_databases,
            object_nodes=object_nodes,
        )

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
                    table_node = self._resolve_object_node(
                        db,
                        name=object_ref.name,
                        object_type=object_ref.object_type,
                        object_nodes=object_nodes,
                        metadata_aliases=metadata_aliases,
                    )
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
                    table_node = self._resolve_object_node(
                        db,
                        name=object_ref.name,
                        object_type=object_ref.object_type,
                        object_nodes=object_nodes,
                        metadata_aliases=metadata_aliases,
                    )
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
                    table_node = self._resolve_object_node(
                        db,
                        name=object_ref.name,
                        object_type=object_ref.object_type,
                        object_nodes=object_nodes,
                        metadata_aliases=metadata_aliases,
                    )
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
                    table_node = self._resolve_object_node(
                        db,
                        name=object_ref.name,
                        object_type=object_ref.object_type,
                        object_nodes=object_nodes,
                        metadata_aliases=metadata_aliases,
                    )
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
                java_files = sorted(java_root.rglob("*.java"))
                java_results = [JavaSqlParser().parse_file(java_file) for java_file in java_files]
                java_api_facts = [
                    endpoint
                    for java_file in java_files
                    for endpoint in parse_controller_endpoints(java_file)
                ]
                reduced_java_results = reduce_java_modules(java_results)
                reduced_api_results = reduce_java_api_endpoints(java_api_facts, reduced_java_results)
                for java_result in java_results:
                    reduced_java_result = reduced_java_results[java_result.module_name]
                    java_node = self._get_or_create_node(
                        db,
                        "java_module",
                        f"java_module:{java_result.module_name}",
                        java_result.module_name,
                    )
                    for table_name in reduced_java_result.read_tables:
                        table_node = self._resolve_object_node(
                            db,
                            name=table_name,
                            object_type="data_table",
                            object_nodes=object_nodes,
                            metadata_aliases=metadata_aliases,
                        )
                        self._ensure_edge(db, "READS", java_node.id, table_node.id)
                    for table_name in reduced_java_result.write_tables:
                        table_node = self._resolve_object_node(
                            db,
                            name=table_name,
                            object_type="data_table",
                            object_nodes=object_nodes,
                            metadata_aliases=metadata_aliases,
                        )
                        self._ensure_edge(db, "WRITES", java_node.id, table_node.id)
                    # Preserve method boundaries while allowing stable call-chain reduction.
                    for method in reduced_java_result.methods.values():
                        method_actor = f"{java_node.key}#{method.method_name}"
                        for table_name in method.read_tables:
                            table_node = self._resolve_object_node(
                                db,
                                name=table_name,
                                object_type="data_table",
                                object_nodes=object_nodes,
                                metadata_aliases=metadata_aliases,
                            )
                            fact_edges.append(("READS", method_actor, table_node.key))
                        for table_name in method.write_tables:
                            table_node = self._resolve_object_node(
                                db,
                                name=table_name,
                                object_type="data_table",
                                object_nodes=object_nodes,
                                metadata_aliases=metadata_aliases,
                            )
                            fact_edges.append(("WRITES", method_actor, table_node.key))
                for endpoint in reduced_api_results:
                    api_node = self._get_or_create_node(
                        db,
                        "api_endpoint",
                        endpoint.endpoint_key,
                        f"{endpoint.http_method} {endpoint.route}",
                    )
                    api_payload = dict(api_node.payload or {})
                    api_payload["object_type"] = "api_endpoint"
                    api_payload["http_method"] = endpoint.http_method
                    api_payload["route"] = endpoint.route
                    api_node.payload = api_payload
                    db.flush()
                    for table_name in endpoint.read_tables:
                        table_node = self._resolve_object_node(
                            db,
                            name=table_name,
                            object_type="data_table",
                            object_nodes=object_nodes,
                            metadata_aliases=metadata_aliases,
                        )
                        self._ensure_edge(db, "READS", api_node.id, table_node.id)
                    for table_name in endpoint.write_tables:
                        table_node = self._resolve_object_node(
                            db,
                            name=table_name,
                            object_type="data_table",
                            object_nodes=object_nodes,
                            metadata_aliases=metadata_aliases,
                        )
                        self._ensure_edge(db, "WRITES", api_node.id, table_node.id)

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

    def get_self_loop_summary(self, db: Session) -> dict[str, Any]:
        """Return grouped `FLOWS_TO` self-loop counts for review-oriented analysis pages."""

        rows = db.execute(
            select(Node, func.count(Edge.id).label("self_loop_count"))
            .join(Edge, Edge.src_node_id == Node.id)
            .where(
                Node.type.in_(("table", "data_object")),
                Edge.type == "FLOWS_TO",
                Edge.src_node_id == Edge.dst_node_id,
                Edge.dst_node_id == Node.id,
            )
            .group_by(Node.id)
            .order_by(func.count(Edge.id).desc(), Node.name.asc(), Node.id.asc())
        ).all()

        items = [
            {
                **_serialize_object(node),
                "self_loop_count": int(self_loop_count),
            }
            for node, self_loop_count in rows
        ]

        return {
            "summary": {
                "table_count": len(items),
                "self_loop_count": sum(item["self_loop_count"] for item in items),
            },
            "items": items,
        }

    def get_cycle_group_summary(self, db: Session) -> dict[str, Any]:
        """Group multi-table closed loops by strongly connected component."""

        table_rows = list(
            db.scalars(select(Node).where(Node.type.in_(("table", "data_object"))).order_by(Node.id.asc())).all()
        )
        node_by_id = {node.id: node for node in table_rows}
        adjacency: dict[int, set[int]] = {node.id: set() for node in table_rows}
        reverse_adjacency: dict[int, set[int]] = {node.id: set() for node in table_rows}

        edge_rows = db.execute(
            select(Edge.src_node_id, Edge.dst_node_id).where(Edge.type == "FLOWS_TO")
        ).all()
        edge_pairs: list[tuple[int, int]] = []
        for source_id, target_id in edge_rows:
            if source_id == target_id:
                continue
            if source_id not in node_by_id or target_id not in node_by_id:
                continue
            adjacency[source_id].add(target_id)
            reverse_adjacency[target_id].add(source_id)
            edge_pairs.append((source_id, target_id))

        visit_order: list[int] = []
        seen: set[int] = set()

        def dfs_forward(node_id: int) -> None:
            if node_id in seen:
                return
            seen.add(node_id)
            for next_id in adjacency.get(node_id, ()):
                dfs_forward(next_id)
            visit_order.append(node_id)

        for node_id in adjacency:
            dfs_forward(node_id)

        components: list[list[int]] = []
        assigned: set[int] = set()

        def dfs_reverse(node_id: int, bucket: list[int]) -> None:
            if node_id in assigned:
                return
            assigned.add(node_id)
            bucket.append(node_id)
            for next_id in reverse_adjacency.get(node_id, ()):
                dfs_reverse(next_id, bucket)

        for node_id in reversed(visit_order):
            if node_id in assigned:
                continue
            component: list[int] = []
            dfs_reverse(node_id, component)
            if len(component) >= 2:
                components.append(component)

        component_sets = [set(component) for component in components]
        items: list[dict[str, Any]] = []
        total_edge_count = 0
        total_table_count = 0

        for index, component_ids in enumerate(
            sorted(component_sets, key=lambda ids: (-len(ids), sorted(node_by_id[node_id].name for node_id in ids))),
            start=1,
        ):
            tables = list(node_by_id[node_id] for node_id in component_ids)
            cycle_edge_count_by_node: dict[int, int] = {node.id: 0 for node in tables}
            edge_count = sum(
                1 for source_id, target_id in edge_pairs if source_id in component_ids and target_id in component_ids
            )
            for source_id, target_id in edge_pairs:
                if source_id in component_ids and target_id in component_ids:
                    cycle_edge_count_by_node[source_id] += 1
                    cycle_edge_count_by_node[target_id] += 1
            tables.sort(key=lambda node: (-cycle_edge_count_by_node[node.id], node.name, node.id))
            total_edge_count += edge_count
            total_table_count += len(tables)
            items.append(
                {
                    "group_key": f"cycle_group:{index}",
                    "table_count": len(tables),
                    "edge_count": edge_count,
                    "tables": [
                        {
                            **_serialize_object(node),
                            "cycle_edge_count": cycle_edge_count_by_node[node.id],
                        }
                        for node in tables
                    ],
                }
            )

        return {
            "summary": {
                "group_count": len(items),
                "table_count": total_table_count,
                "edge_count": total_edge_count,
            },
            "items": items,
        }

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
        api_endpoint_stmt = (
            select(Node)
            .join(Edge, Edge.src_node_id == Node.id)
            .where(
                Node.type == "api_endpoint",
                Edge.dst_node_id == table.id,
                Edge.type.in_(("READS", "WRITES")),
            )
            .order_by(Node.name.asc(), Node.id.asc())
        )
        api_endpoints = list(db.scalars(api_endpoint_stmt).all())
        downstream_nodes = sorted([*downstream_tables, *api_endpoints], key=lambda node: (node.name, node.id))

        return {
            "table": _serialize_object(table),
            "upstream_tables": [_serialize_object(node) for node in upstream_tables],
            "downstream_tables": [_serialize_object(node) for node in downstream_nodes],
            "related_objects": self._related_objects(db, table),
        }

    def get_connected_table_lineage(self, db: Session, table_key: str) -> dict[str, Any]:
        """Return the detail-page directional lineage subgraph in one backend round-trip."""

        table = db.scalar(select(Node).where(Node.type.in_(("table", "data_object")), Node.key == table_key))
        if table is None:
            return {"table_lineage": None, "items": []}

        upstream_ids = self._collect_directional_table_ids(db, table.id, direction="upstream")
        downstream_ids = self._collect_directional_table_ids(db, table.id, direction="downstream")
        allowed_ids = upstream_ids | downstream_ids | {table.id}
        raw_lineages = [
            self.get_table_lineage(db, node.key)
            for node in db.scalars(
                select(Node)
                .where(Node.id.in_(allowed_ids))
                .order_by(Node.name.asc(), Node.id.asc())
            ).all()
        ]
        items = self._collect_directional_lineages(
            table.key,
            [lineage for lineage in raw_lineages if lineage is not None],
        )
        table_lineage = next(
            (item for item in items if item["table"] and item["table"]["key"] == table.key),
            None,
        )
        return {"table_lineage": table_lineage, "items": items}

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

    def _collect_directional_table_ids(
        self, db: Session, start_table_id: int, *, direction: str
    ) -> set[int]:
        """Walk only upstream or downstream FLOWS_TO edges from one table-like node."""

        frontier = {start_table_id}
        visited: set[int] = set()

        while frontier:
            if direction == "upstream":
                next_ids = db.scalars(
                    select(Edge.src_node_id).where(
                        Edge.type == "FLOWS_TO",
                        Edge.dst_node_id.in_(frontier),
                    )
                ).all()
            else:
                next_ids = db.scalars(
                    select(Edge.dst_node_id).where(
                        Edge.type == "FLOWS_TO",
                        Edge.src_node_id.in_(frontier),
                    )
                ).all()

            next_frontier: set[int] = set()
            for node_id in next_ids:
                if node_id == start_table_id or node_id in visited:
                    continue
                node = db.get(Node, node_id)
                if node is None or node.type not in {"table", "data_object"}:
                    continue
                visited.add(node_id)
                next_frontier.add(node_id)
            frontier = next_frontier

        return visited

    def _collect_directional_lineages(
        self, current_table_key: str, lineages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Keep only monotonic upstream/downstream paths around the current table."""

        lineage_by_key: dict[str, dict[str, Any]] = {}
        upstream_by_node: dict[str, set[str]] = {}
        downstream_by_node: dict[str, set[str]] = {}

        def ensure_direction_map(direction_map: dict[str, set[str]], key: str) -> set[str]:
            if key not in direction_map:
                direction_map[key] = set()
            return direction_map[key]

        for lineage in lineages:
            table = lineage.get("table")
            table_key = table.get("key") if table else None
            if not table_key:
                continue
            lineage_by_key[table_key] = lineage
            ensure_direction_map(upstream_by_node, table_key)
            ensure_direction_map(downstream_by_node, table_key)

            for upstream in lineage.get("upstream_tables", []):
                ensure_direction_map(upstream_by_node, table_key).add(upstream["key"])
                ensure_direction_map(downstream_by_node, upstream["key"]).add(table_key)

            for downstream in lineage.get("downstream_tables", []):
                ensure_direction_map(downstream_by_node, table_key).add(downstream["key"])
                ensure_direction_map(upstream_by_node, downstream["key"]).add(table_key)

        def walk_direction(seed: str, adjacency: dict[str, set[str]]) -> set[str]:
            queue = [seed]
            visited: set[str] = set()
            while queue:
                key = queue.pop(0)
                if key in visited:
                    continue
                visited.add(key)
                queue.extend(next_key for next_key in adjacency.get(key, set()) if next_key not in visited)
            return visited

        def collect_distance_map(seed: str, adjacency: dict[str, set[str]]) -> dict[str, int]:
            queue: list[tuple[str, int]] = [(seed, 0)]
            distance_by_node: dict[str, int] = {}
            while queue:
                key, distance = queue.pop(0)
                if key in distance_by_node:
                    continue
                distance_by_node[key] = distance
                queue.extend(
                    (next_key, distance + 1)
                    for next_key in adjacency.get(key, set())
                    if next_key not in distance_by_node
                )
            return distance_by_node

        upstream_reachable = walk_direction(current_table_key, upstream_by_node)
        downstream_reachable = walk_direction(current_table_key, downstream_by_node)
        upstream_distance = collect_distance_map(current_table_key, upstream_by_node)
        downstream_distance = collect_distance_map(current_table_key, downstream_by_node)
        allowed_keys = upstream_reachable | downstream_reachable | {current_table_key}

        filtered_lineages: list[dict[str, Any]] = []
        for key in sorted(allowed_keys):
            lineage = lineage_by_key.get(key)
            if lineage is None:
                continue

            def keep_upstream(table: dict[str, Any]) -> bool:
                if table["key"] not in allowed_keys:
                    return False
                source_upstream_distance = upstream_distance.get(table["key"])
                target_upstream_distance = upstream_distance.get(key)
                if (
                    source_upstream_distance is not None
                    and target_upstream_distance is not None
                    and source_upstream_distance == target_upstream_distance + 1
                ):
                    return True

                source_downstream_distance = downstream_distance.get(table["key"])
                target_downstream_distance = downstream_distance.get(key)
                return (
                    source_downstream_distance is not None
                    and target_downstream_distance is not None
                    and source_downstream_distance + 1 == target_downstream_distance
                )

            def keep_downstream(table: dict[str, Any]) -> bool:
                if table["key"] not in allowed_keys:
                    return False
                source_upstream_distance = upstream_distance.get(key)
                target_upstream_distance = upstream_distance.get(table["key"])
                if (
                    source_upstream_distance is not None
                    and target_upstream_distance is not None
                    and source_upstream_distance == target_upstream_distance + 1
                ):
                    return True

                source_downstream_distance = downstream_distance.get(key)
                target_downstream_distance = downstream_distance.get(table["key"])
                return (
                    source_downstream_distance is not None
                    and target_downstream_distance is not None
                    and source_downstream_distance + 1 == target_downstream_distance
                )

            filtered_lineages.append(
                {
                    **lineage,
                    "upstream_tables": [
                        table for table in lineage.get("upstream_tables", []) if keep_upstream(table)
                    ],
                    "downstream_tables": [
                        table for table in lineage.get("downstream_tables", []) if keep_downstream(table)
                    ],
                }
            )

        return filtered_lineages

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
