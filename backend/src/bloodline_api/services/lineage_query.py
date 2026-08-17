"""Query helpers for scan, job, and table lineage APIs."""

from __future__ import annotations

from datetime import datetime, timezone
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, delete, func, select, text
from sqlalchemy.orm import Session

from bloodline_api.connectors.mysql_metadata import MySQLMetadataLoader
from bloodline_api.connectors.mysql_metadata import MySQLMetadataConnectionError
from bloodline_api.connectors.mysql_metadata import MySQLMetadataObject
from bloodline_api.connectors.mysql_metadata import build_mysql_metadata_request
from bloodline_api.models import Edge, FieldEdge, Node, ObjectMetadata, ObjectMetadataColumn, ScanFailure, ScanRun
from bloodline_api.parsers.java_controller_parser import parse_controller_endpoints
from bloodline_api.parsers.java_lineage_reducer import reduce_java_api_endpoints
from bloodline_api.parsers.java_lineage_reducer import reduce_java_modules
from bloodline_api.parsers.java_sql_parser import JavaSqlParser
from bloodline_api.parsers.repo_parser import RepoParser
from bloodline_api.parsers.sql_table_extractor import extract_column_lineage_with_error
from bloodline_api.parsers.sql_table_extractor import extract_tables_with_error
from bloodline_api.services.graph_builder import build_table_flows

BACKEND_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_OBJECT_TYPE = "data_table"
CRUD_READ_METHODS = {
    "selectPage",
    "selectList",
    "selectOne",
    "selectById",
    "selectBatchIds",
    "selectMaps",
    "selectCount",
}
CRUD_WRITE_METHODS = {
    "insert",
    "updateById",
    "update",
    "deleteById",
    "delete",
    "deleteBatchIds",
}
SERVICE_IMPL_ENTITY_PATTERN = re.compile(r"ServiceImpl<\s*[\w\.\[\]<>]+\s*,\s*([\w\.\[\]<>]+)")
ISERVICE_PATTERN = re.compile(r"IService<\s*([\w\.\[\]<>]+)")


def _resolve_input_path(value: str) -> Path:
    """Resolve relative scan inputs against the backend workspace."""

    normalized = value.strip().replace("\\ ", " ")
    path = Path(normalized)
    return path if path.is_absolute() else BACKEND_ROOT / path


def _normalized_input_values(values: list[str] | None, single_value: str | None) -> list[str]:
    """Merge legacy single-value inputs with newer multi-value lists."""

    merged: list[str] = []
    if values:
        merged.extend(item for item in values if item)
    if single_value:
        merged.append(single_value)

    deduped: list[str] = []
    for item in merged:
        if item not in deduped:
            deduped.append(item)
    return deduped


def _normalize_java_type_name(type_ref: str) -> str:
    """Normalize one Java type reference to its simple outer type name."""

    normalized = re.sub(r"<.*>$", "", type_ref.strip())
    normalized = re.sub(r">+$", "", normalized)
    normalized = re.sub(r"\[\]$", "", normalized)
    return normalized.split(".")[-1]


def _mybatis_plus_missing_evidence_reason(
    source_module: Any,
    call: str,
    modules_by_name: dict[str, Any],
) -> str | None:
    """Return the MyBatis-Plus-specific missing-evidence label for one receiver-qualified CRUD call."""

    if "." not in call:
        return None

    receiver, callee = call.split(".", 1)
    if callee not in CRUD_READ_METHODS and callee not in CRUD_WRITE_METHODS:
        return None

    declared_type = source_module.receiver_types.get(receiver)
    if declared_type is None:
        return None

    mapper_module_name = _normalize_java_type_name(declared_type)

    mapper_module = modules_by_name.get(mapper_module_name)
    if mapper_module is None:
        return "crud_method_without_table_binding"

    entity_name = mapper_module.basemapper_entity
    if not entity_name and mapper_module.extended_type:
        service_impl_match = SERVICE_IMPL_ENTITY_PATTERN.search(mapper_module.extended_type)
        if service_impl_match is not None:
            entity_name = _normalize_java_type_name(service_impl_match.group(1))
        else:
            iservice_match = ISERVICE_PATTERN.search(mapper_module.extended_type)
            if iservice_match is not None:
                entity_name = _normalize_java_type_name(iservice_match.group(1))

    if not entity_name:
        return "mapper_without_basemapper_entity"

    entity_module = modules_by_name.get(entity_name)
    if entity_module is None or not entity_module.table_name:
        return "entity_without_table_name"

    return None


def _resolve_repo_paths(values: list[str]) -> list[Path]:
    """Resolve and validate repo file paths with user-friendly errors."""

    resolved_paths: list[Path] = []
    for index, value in enumerate(values, start=1):
        path = _resolve_input_path(value)
        if not path.exists():
            raise ValueError(f"第 {index} 个 Repo 文件路径不存在：{value}。请检查路径后重试。")
        if not path.is_file():
            raise ValueError(f"第 {index} 个 Repo 文件路径不是文件：{value}。请填写文件路径后重试。")
        resolved_paths.append(path)
    return resolved_paths


def _resolve_java_roots(values: list[str]) -> list[Path]:
    """Resolve and validate Java source directories with user-friendly errors."""

    resolved_paths: list[Path] = []
    for index, value in enumerate(values, start=1):
        path = _resolve_input_path(value)
        if not path.exists():
            raise ValueError(f"第 {index} 个 Java 源码目录不存在：{value}。请检查路径后重试。")
        if not path.is_dir():
            raise ValueError(f"第 {index} 个 Java 源码目录不是目录：{value}。请填写目录路径后重试。")
        resolved_paths.append(path)
    return resolved_paths


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

    metadata = node.object_metadata
    display_name = metadata.comment if metadata is not None and metadata.comment else node.name
    payload = {
        "id": node.id,
        "key": node.key,
        "name": node.name,
        "display_name": display_name,
        "object_type": node.payload.get("object_type", DEFAULT_OBJECT_TYPE),
        "payload": node.payload,
    }
    if metadata is not None:
        payload["metadata"] = {
            "database_name": metadata.database_name,
            "object_name": metadata.object_name,
            "object_kind": metadata.object_kind,
            "comment": metadata.comment,
            "column_count": len(metadata.columns),
            "view_definition": metadata.view_definition,
            "view_parse_status": metadata.view_parse_status,
            "view_parse_error": metadata.view_parse_error,
            "metadata_source": metadata.metadata_source,
        }
    return payload


def _scan_run_payload(scan_run: ScanRun | None) -> dict[str, Any] | None:
    """Serialize a scan run for the latest-failures endpoint."""

    if scan_run is None:
        return None

    return {
        "id": scan_run.id,
        "status": scan_run.status,
        "inputs": scan_run.inputs or {},
        "started_at": scan_run.started_at,
        "finished_at": scan_run.finished_at,
        "created_at": scan_run.created_at,
    }


def _scan_failure_payload(scan_failure: ScanFailure) -> dict[str, Any]:
    """Serialize one persisted failure record."""

    return {
        "id": scan_failure.id,
        "scan_run_id": scan_failure.scan_run_id,
        "source_type": scan_failure.source_type,
        "file_path": scan_failure.file_path,
        "failure_type": scan_failure.failure_type,
        "message": scan_failure.message,
        "object_key": scan_failure.object_key,
        "sql_snippet": scan_failure.sql_snippet,
        "created_at": scan_failure.created_at,
    }


class LineageQueryService:
    """Orchestrate scan persistence and graph-shaped query responses."""

    def _empty_related_objects(self) -> dict[str, list[dict[str, Any]]]:
        """Return a stable empty related-objects payload."""

        return {
            "jobs": [],
            "java_modules": [],
            "api_endpoints": [],
            "transformations": [],
        }

    def reset_graph_state(self, db: Session) -> None:
        """Clear persisted graph entities before a full rescan rebuild."""

        db.execute(delete(ObjectMetadataColumn))
        db.execute(delete(ObjectMetadata))
        db.execute(delete(FieldEdge))
        db.execute(delete(Edge))
        db.execute(delete(Node))
        db.flush()

    def _record_scan_failure(
        self,
        db: Session,
        *,
        scan_run: ScanRun,
        source_type: str,
        file_path: str,
        failure_type: str,
        message: str,
        object_key: str | None = None,
        sql_snippet: str | None = None,
    ) -> ScanFailure:
        """Persist one scan failure tied to the current scan run."""

        failure = ScanFailure(
            scan_run_id=scan_run.id,
            source_type=source_type,
            file_path=file_path,
            failure_type=failure_type,
            message=message,
            object_key=object_key,
            sql_snippet=sql_snippet,
        )
        db.add(failure)
        db.flush()
        return failure

    def _frms_dsn(self, base_dsn: str | None) -> str:
        """Derive frms database DSN from the user-provided MySQL DSN."""

        if not base_dsn:
            return "mysql+pymysql://root:root@127.0.0.1:3306/frms"
        parsed = urlparse(base_dsn)
        return urlunparse(parsed._replace(path="/frms"))

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
                view_definition=metadata_object.view_definition,
                view_parse_status="not_applicable",
                view_parse_error=None,
                metadata_source="mysql_information_schema",
            )
            db.add(metadata)
            db.flush()
        else:
            metadata.database_name = metadata_object.database_name
            metadata.object_name = metadata_object.object_name
            metadata.object_kind = metadata_object.object_kind
            metadata.comment = metadata_object.comment
            metadata.view_definition = metadata_object.view_definition
            metadata.metadata_source = "mysql_information_schema"
        if metadata_object.object_kind == "view":
            metadata.view_parse_status = "not_applicable"
            metadata.view_parse_error = None
        else:
            metadata.view_parse_status = "not_applicable"
            metadata.view_parse_error = None

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

    def _derive_view_definition_facts(
        self,
        db: Session,
        *,
        scan_run: ScanRun,
        object_nodes: dict[str, Node],
        metadata_aliases: dict[str, Node],
        fact_edges: list[tuple[str, str, str]],
    ) -> None:
        """Turn parsed view definitions into table-flow facts without failing the full scan."""

        for node in list(object_nodes.values()):
            metadata = node.object_metadata
            if metadata is None or metadata.object_kind != "view" or not metadata.view_definition:
                continue

            reads, _writes, parse_error = extract_tables_with_error(metadata.view_definition)
            if reads:
                metadata.view_parse_status = "parsed"
                metadata.view_parse_error = None
                for table_name in sorted(reads):
                    table_node = self._resolve_object_node(
                        db,
                        name=table_name,
                        object_type="data_table",
                        object_nodes=object_nodes,
                        metadata_aliases=metadata_aliases,
                    )
                    fact_edges.append(("READS", node.key, table_node.key))
                fact_edges.append(("WRITES", node.key, node.key))
                # Column-level lineage for views
                self._persist_field_edges_from_sql(
                    db,
                    scan_run=scan_run,
                    sql=metadata.view_definition,
                    actor_key=node.key,
                    object_nodes=object_nodes,
                    metadata_aliases=metadata_aliases,
                    source_type="metadata",
                    file_path=f"{metadata.database_name}.{metadata.object_name}",
                )
            else:
                metadata.view_parse_status = "failed"
                metadata.view_parse_error = parse_error or "无法从 VIEW_DEFINITION 中识别底层对象，请检查 SQL 方言或定义内容。"
                self._record_scan_failure(
                    db,
                    scan_run=scan_run,
                    source_type="metadata",
                    file_path=f"{metadata.database_name}.{metadata.object_name}",
                    failure_type="view_definition_parse_error",
                    message=metadata.view_parse_error,
                    object_key=node.key,
                    sql_snippet=metadata.view_definition,
                )
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

    def _load_finereport_datasets(
        self,
        db: Session,
        *,
        object_nodes: dict[str, Node],
        metadata_aliases: dict[str, Node],
        fact_edges: list[tuple[str, str, str]],
        scan_run: ScanRun,
        mysql_dsn: str | None = None,
    ) -> None:
        """Load table-to-FineReport-file lineage from frms.comm_finereport_record_details.

        For each FineReport record, parse the SQL in ``data_sql`` to obtain the
        source tables/views and create ``FLOWS_TO`` edges from those sources to
        the report file identified by ``report_path``.
        """

        mysql_dsn = self._frms_dsn(mysql_dsn)
        try:
            engine = create_engine(mysql_dsn, future=True, pool_pre_ping=True)
            with engine.connect() as connection:
                rows = connection.execute(
                    text("SELECT report_path, data_sql FROM frms.comm_finereport_record_details")
                ).mappings()
                for row in rows:
                    report_path = row["report_path"]
                    data_sql = row["data_sql"]
                    if not report_path or not data_sql:
                        continue
                    read_tables, _write_tables, error = extract_tables_with_error(data_sql)
                    if error:
                        self._record_scan_failure(
                            db,
                            scan_run=scan_run,
                            source_type="finereport",
                            file_path=report_path,
                            failure_type="sql_parse_error",
                            message=error,
                        )
                        continue
                    file_key = f"finereport_file:{report_path}"
                    file_node = self._get_or_create_node(
                        db, "report_file", file_key, report_path
                    )
                    file_payload = dict(file_node.payload or {})
                    file_payload["object_type"] = "report_file"
                    file_payload.setdefault("source", "finereport")
                    file_node.payload = file_payload
                    object_nodes[file_node.key] = file_node
                    for table_name in read_tables:
                        table_node = self._resolve_object_node(
                            db,
                            name=table_name,
                            object_type="data_table",
                            object_nodes=object_nodes,
                            metadata_aliases=metadata_aliases,
                        )
                        self._ensure_edge(
                            db,
                            "FLOWS_TO",
                            table_node.id,
                            file_node.id,
                            is_derived=True,
                            payload={"source": "finereport"},
                        )
                        fact_edges.append(("READS", f"finereport:{report_path}", table_node.key))
            engine.dispose()
        except Exception as exc:
            self._record_scan_failure(
                db,
                scan_run=scan_run,
                source_type="finereport",
                file_path=mysql_dsn,
                failure_type=exc.__class__.__name__,
                message=str(exc),
            )

    def _load_api_page_mappings(
        self,
        db: Session,
        *,
        object_nodes: dict[str, Node],
        scan_run: ScanRun,
        mysql_dsn: str | None = None,
    ) -> None:
        """Load API-to-page mappings from frms.comm_permission_mapping."""

        mysql_dsn = self._frms_dsn(mysql_dsn)
        try:
            engine = create_engine(mysql_dsn, future=True, pool_pre_ping=True)
            with engine.connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT
                            first_level_menu,
                            second_level_menu,
                            third_level_menu,
                            fourth_level_menu,
                            menu_name,
                            menu_url,
                            page_name,
                            page_type,
                            api_url,
                            api_function,
                            request_method
                        FROM frms.comm_permission_mapping
                        WHERE delete_status = 0
                        """
                    )
                ).mappings()

                for row in rows:
                    api_url = row["api_url"]
                    if not api_url or api_url == "(无API调用)":
                        continue

                    normalized_url = api_url.strip()
                    if normalized_url.startswith("/"):
                        normalized_url = normalized_url[1:]

                    request_method = row["request_method"]
                    if (
                        request_method
                        and request_method.strip()
                        and request_method.strip() != "-"
                    ):
                        api_name = f"{request_method.strip().upper()} {normalized_url}"
                    else:
                        api_name = normalized_url

                    api_key = f"api:{api_name}"

                    menu_parts = [
                        row["first_level_menu"],
                        row["second_level_menu"],
                        row["third_level_menu"],
                        row["fourth_level_menu"],
                        row["menu_name"],
                    ]
                    menu_path = " > ".join(
                        str(p).strip() for p in menu_parts if p and str(p).strip()
                    )

                    if not menu_path:
                        continue

                    page_key = f"page:{menu_path}"
                    page_name = menu_path

                    api_node = self._get_or_create_node(
                        db, "api_endpoint", api_key, api_name
                    )
                    api_payload = dict(api_node.payload or {})
                    api_payload["object_type"] = "api_endpoint"
                    api_payload.setdefault("source", "permission_mapping")
                    api_node.payload = api_payload
                    object_nodes[api_node.key] = api_node

                    page_node = db.scalar(select(Node).where(Node.key == page_key))
                    if page_node is None:
                        page_node = Node(
                            type="web_page",
                            key=page_key,
                            name=page_name,
                            payload={
                                "source": "permission_mapping",
                                "object_type": "web_page",
                                "menu_url": row["menu_url"],
                                "page_name": row["page_name"],
                                "page_type": row["page_type"],
                                "api_function": row["api_function"],
                            },
                        )
                        db.add(page_node)
                        db.flush()
                    object_nodes[page_node.key] = page_node

                    self._ensure_edge(
                        db,
                        "FLOWS_TO",
                        api_node.id,
                        page_node.id,
                        is_derived=True,
                        payload={"source": "permission_mapping"},
                    )

            engine.dispose()
        except Exception as exc:
            self._record_scan_failure(
                db,
                scan_run=scan_run,
                source_type="permission_mapping",
                file_path=mysql_dsn,
                failure_type=exc.__class__.__name__,
                message=str(exc),
            )

    def _load_finereport_config_lineage(
        self,
        db: Session,
        *,
        object_nodes: dict[str, Node],
        scan_run: ScanRun,
        mysql_dsn: str | None = None,
    ) -> None:
        """Load FineReport file-to-menu lineage from frms.COMM_FINEREPORT_CONFIG."""

        mysql_dsn = self._frms_dsn(mysql_dsn)
        try:
            engine = create_engine(mysql_dsn, future=True, pool_pre_ping=True)
            with engine.connect() as connection:
                rows = connection.execute(
                    text(
                        """
                        SELECT reportpath_tidb, modulepath
                        FROM frms.COMM_FINEREPORT_CONFIG
                        WHERE reportpath_tidb IS NOT NULL AND reportpath_tidb != ''
                        """
                    )
                ).mappings()

                for row in rows:
                    report_path = row["reportpath_tidb"].strip()
                    menu_path = row["modulepath"].strip()
                    if not report_path or not menu_path:
                        continue

                    file_key = f"finereport_file:{report_path}"
                    file_name = report_path
                    menu_key = f"menu:{menu_path}"
                    menu_name = menu_path

                    file_node = self._get_or_create_node(
                        db, "report_file", file_key, file_name
                    )
                    file_payload = dict(file_node.payload or {})
                    file_payload["object_type"] = "report_file"
                    file_payload.setdefault("source", "finereport_config")
                    file_node.payload = file_payload
                    object_nodes[file_node.key] = file_node

                    menu_node = self._get_or_create_node(
                        db, "menu", menu_key, menu_name
                    )
                    menu_payload = dict(menu_node.payload or {})
                    menu_payload["object_type"] = "menu"
                    menu_payload.setdefault("source", "finereport_config")
                    menu_node.payload = menu_payload
                    object_nodes[menu_node.key] = menu_node

                    self._ensure_edge(
                        db,
                        "FLOWS_TO",
                        file_node.id,
                        menu_node.id,
                        is_derived=True,
                        payload={"source": "finereport_config"},
                    )

            engine.dispose()
        except Exception as exc:
            self._record_scan_failure(
                db,
                scan_run=scan_run,
                source_type="finereport_config",
                file_path=mysql_dsn,
                failure_type=exc.__class__.__name__,
                message=str(exc),
            )

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

    def _ensure_field_edge(
        self,
        db: Session,
        src_node_id: int,
        dst_node_id: int,
        src_field: str,
        dst_field: str,
        *,
        edge_id: int | None = None,
        is_derived: bool = False,
        payload: dict[str, Any] | None = None,
    ) -> FieldEdge:
        """Ensure a unique field-level edge exists for the given mapping."""

        field_edge = db.scalar(
            select(FieldEdge).where(
                FieldEdge.src_node_id == src_node_id,
                FieldEdge.dst_node_id == dst_node_id,
                FieldEdge.src_field == src_field,
                FieldEdge.dst_field == dst_field,
                FieldEdge.is_derived == is_derived,
            )
        )
        if field_edge is not None:
            return field_edge

        field_edge = FieldEdge(
            edge_id=edge_id,
            src_node_id=src_node_id,
            dst_node_id=dst_node_id,
            src_field=src_field,
            dst_field=dst_field,
            is_derived=is_derived,
            payload=payload or {},
        )
        db.add(field_edge)
        db.flush()
        return field_edge

    def _persist_field_edges_from_sql(
        self,
        db: Session,
        *,
        scan_run: ScanRun,
        sql: str,
        actor_key: str,
        object_nodes: dict[str, Node],
        metadata_aliases: dict[str, Node],
        source_type: str,
        file_path: str,
    ) -> None:
        """Parse one SQL fragment for column lineage and persist any explicit field mappings."""

        field_mappings, parse_error = extract_column_lineage_with_error(sql)
        if parse_error:
            self._record_scan_failure(
                db,
                scan_run=scan_run,
                source_type=source_type,
                file_path=file_path,
                failure_type="column_lineage_parse_error",
                message=parse_error,
                object_key=actor_key,
                sql_snippet=sql,
            )
        for src_table, src_field, dst_table, dst_field in field_mappings:
            src_node = self._resolve_object_node(
                db,
                name=src_table,
                object_type="data_table",
                object_nodes=object_nodes,
                metadata_aliases=metadata_aliases,
            )
            dst_node = self._resolve_object_node(
                db,
                name=dst_table,
                object_type="data_table",
                object_nodes=object_nodes,
                metadata_aliases=metadata_aliases,
            )
            self._ensure_field_edge(
                db,
                src_node_id=src_node.id,
                dst_node_id=dst_node.id,
                src_field=src_field,
                dst_field=dst_field,
                payload={"actor": actor_key, "source_type": source_type},
            )

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
        repo_paths: list[str] | None = None,
        java_source_root: str | None = None,
        java_source_roots: list[str] | None = None,
        mysql_dsn: str | None = None,
        metadata_databases: list[str] | None = None,
        inputs: dict[str, Any] | None = None,
    ) -> ScanRun:
        """Run the MVP scan pipeline and persist the resulting graph state."""

        _ = mysql_dsn
        _ = metadata_databases
        self.reset_graph_state(db)
        now = datetime.now(timezone.utc)
        scan_run = ScanRun(status="running", started_at=now, inputs=inputs or {})
        db.add(scan_run)
        db.flush()

        fact_edges: list[tuple[str, str, str]] = []
        object_nodes: dict[str, Node] = {}
        metadata_aliases: dict[str, Node] = {}
        try:
            metadata_aliases = self._load_mysql_metadata_nodes(
                db,
                mysql_dsn=mysql_dsn,
                metadata_databases=metadata_databases,
                object_nodes=object_nodes,
            )
            self._derive_view_definition_facts(
                db,
                scan_run=scan_run,
                object_nodes=object_nodes,
                metadata_aliases=metadata_aliases,
                fact_edges=fact_edges,
            )
        except MySQLMetadataConnectionError as exc:
            self._record_scan_failure(
                db,
                scan_run=scan_run,
                source_type="metadata",
                file_path=mysql_dsn or "mysql_dsn",
                failure_type=exc.__class__.__name__,
                message=str(exc),
            )
            scan_run.status = "failed"
            scan_run.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise

        for repo_file in _resolve_repo_paths(_normalized_input_values(repo_paths, repo_path)):
            try:
                repo_result = RepoParser().parse_file(repo_file)
            except Exception as exc:  # pragma: no cover - defensive scan record
                self._record_scan_failure(
                    db,
                    scan_run=scan_run,
                    source_type="kettle",
                    file_path=str(repo_file),
                    failure_type=exc.__class__.__name__,
                    message=str(exc),
                )
                continue
            for failure in repo_result.parse_failures:
                self._record_scan_failure(
                    db,
                    scan_run=scan_run,
                    source_type="kettle",
                    file_path=failure.file_path,
                    failure_type=failure.failure_type,
                    message=failure.message,
                    object_key=failure.object_key,
                    sql_snippet=failure.sql_snippet,
                )
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
                    fact_edges.append(("READS", f"job:{entry_key}", table_node.key))

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
                    fact_edges.append(("WRITES", f"job:{entry_key}", table_node.key))

            # Field-level lineage from repo SQL steps and job entries
            for step_key, sql in repo_result.step_sqls.items():
                transformation_name = step_key.split("::", 1)[0]
                actor_key = f"transformation:{transformation_name}"
                self._persist_field_edges_from_sql(
                    db,
                    scan_run=scan_run,
                    sql=sql,
                    actor_key=actor_key,
                    object_nodes=object_nodes,
                    metadata_aliases=metadata_aliases,
                    source_type="kettle",
                    file_path=str(repo_file),
                )
            for entry_key, sql in repo_result.job_sqls.items():
                job_name = entry_key.split("::", 1)[0]
                actor_key = f"job:{job_name}"
                self._persist_field_edges_from_sql(
                    db,
                    scan_run=scan_run,
                    sql=sql,
                    actor_key=actor_key,
                    object_nodes=object_nodes,
                    metadata_aliases=metadata_aliases,
                    source_type="kettle",
                    file_path=str(repo_file),
                )

        java_files: list[Path] = []
        for java_root in _resolve_java_roots(_normalized_input_values(java_source_roots, java_source_root)):
            java_files.extend(java_root.rglob("*.java"))
        if java_files:
            deduped_java_files = sorted({java_file.resolve(): java_file for java_file in java_files}.values())
            java_results = []
            java_api_facts = []
            for java_file in deduped_java_files:
                try:
                    java_result = JavaSqlParser().parse_file(java_file)
                except Exception as exc:  # pragma: no cover - defensive scan record
                    self._record_scan_failure(
                        db,
                        scan_run=scan_run,
                        source_type="java",
                        file_path=str(java_file),
                        failure_type=exc.__class__.__name__,
                        message=str(exc),
                    )
                    continue
                for failure in java_result.parse_failures:
                    self._record_scan_failure(
                        db,
                        scan_run=scan_run,
                        source_type="java",
                        file_path=failure.file_path,
                        failure_type=failure.failure_type,
                        message=failure.message,
                        object_key=failure.object_key,
                        sql_snippet=failure.sql_snippet,
                    )
                java_results.append(java_result)
                try:
                    java_api_facts.extend(parse_controller_endpoints(java_file))
                except Exception as exc:  # pragma: no cover - defensive scan record
                    self._record_scan_failure(
                        db,
                        scan_run=scan_run,
                        source_type="java",
                        file_path=str(java_file),
                        failure_type=exc.__class__.__name__,
                        message=str(exc),
                    )
                    continue
            reduced_java_results = reduce_java_modules(java_results)
            reduced_api_results = reduce_java_api_endpoints(
                java_api_facts,
                reduced_java_results,
                java_results,
            )
            java_results_by_name = {java_result.module_name: java_result for java_result in java_results}
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
                diagnostics = {
                    "resolved_calls": endpoint.resolved_call_count,
                    "unresolved_calls": endpoint.unresolved_call_count,
                    "unresolved_reasons": [dict(reason) for reason in endpoint.unresolved_reasons],
                    "read_table_count": len(endpoint.read_tables),
                    "write_table_count": len(endpoint.write_tables),
                }
                source_module = java_results_by_name.get(endpoint.controller_module_name)
                if source_module is not None:
                    updated_reasons: list[dict[str, str]] = []
                    for reason in diagnostics["unresolved_reasons"]:
                        mapped_reason = _mybatis_plus_missing_evidence_reason(
                            source_module,
                            reason["call"],
                            java_results_by_name,
                        )
                        if mapped_reason is None:
                            updated_reasons.append(reason)
                            continue
                        updated_reasons.append({"call": reason["call"], "reason": mapped_reason})
                    diagnostics["unresolved_reasons"] = updated_reasons

                api_payload["diagnostics"] = diagnostics
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

            # Field-level lineage from direct Java SQL statements
            for java_result in java_results:
                java_node = self._get_or_create_node(
                    db,
                    "java_module",
                    f"java_module:{java_result.module_name}",
                    java_result.module_name,
                )
                for statement in java_result.statements:
                    if not statement.sql_snippet:
                        continue
                    self._persist_field_edges_from_sql(
                        db,
                        scan_run=scan_run,
                        sql=statement.sql_snippet,
                        actor_key=java_node.key,
                        object_nodes=object_nodes,
                        metadata_aliases=metadata_aliases,
                        source_type="java",
                        file_path=java_result.module_name,
                    )

        self._load_finereport_datasets(
            db,
            object_nodes=object_nodes,
            metadata_aliases=metadata_aliases,
            fact_edges=fact_edges,
            scan_run=scan_run,
            mysql_dsn=mysql_dsn,
        )

        self._load_api_page_mappings(
            db,
            object_nodes=object_nodes,
            scan_run=scan_run,
            mysql_dsn=mysql_dsn,
        )

        self._load_finereport_config_lineage(
            db,
            object_nodes=object_nodes,
            scan_run=scan_run,
            mysql_dsn=mysql_dsn,
        )

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
        """Search table-like objects and API endpoints by key or name for the frontend search page."""

        stmt = select(Node).where(Node.type.in_(("table", "data_object", "api_endpoint", "menu", "report_file")))
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where((Node.key.ilike(pattern)) | (Node.name.ilike(pattern)))
        stmt = stmt.order_by(Node.name.asc(), Node.id.asc())
        return list(db.scalars(stmt).all())

    def list_scan_runs(self, db: Session) -> list[ScanRun]:
        """Return scan runs in reverse chronological order."""

        stmt = select(ScanRun).order_by(ScanRun.created_at.desc(), ScanRun.id.desc())
        return list(db.scalars(stmt).all())

    def record_operation_failure(
        self,
        db: Session,
        *,
        source_type: str,
        file_path: str,
        failure_type: str,
        message: str,
        object_key: str | None = None,
    ) -> ScanFailure:
        """Record a non-scan operation failure under the latest scan run for UI review."""

        latest = next(iter(self.list_scan_runs(db)), None)
        if latest is None:
            latest = ScanRun(status="unknown", inputs={})
            db.add(latest)
            db.flush()

        failure = ScanFailure(
            scan_run_id=latest.id,
            source_type=source_type,
            file_path=file_path,
            failure_type=failure_type,
            message=message,
            object_key=object_key,
        )
        db.add(failure)
        db.commit()
        return failure

    def get_latest_scan_failures(self, db: Session) -> dict[str, Any]:
        """Return grouped scan failures for the most recent scan run."""

        latest = next(iter(self.list_scan_runs(db)), None)
        empty_summary = {
            "scan_run_id": None,
            "failure_count": 0,
            "file_count": 0,
            "source_counts": {"kettle": 0, "java": 0, "metadata": 0, "system": 0, "ui": 0},
        }
        if latest is None:
            return {"scan_run": None, "summary": empty_summary, "groups": []}

        failures = list(
            db.scalars(
                select(ScanFailure)
                .where(ScanFailure.scan_run_id == latest.id)
                .order_by(ScanFailure.source_type.asc(), ScanFailure.file_path.asc(), ScanFailure.id.asc())
            ).all()
        )
        grouped: dict[str, dict[str, list[dict[str, Any]]]] = {}
        source_counts = {"kettle": 0, "java": 0, "metadata": 0, "system": 0, "ui": 0}
        for failure in failures:
            source_counts[failure.source_type] = source_counts.get(failure.source_type, 0) + 1
            grouped.setdefault(failure.source_type, {}).setdefault(failure.file_path, []).append(
                _scan_failure_payload(failure)
            )

        groups: list[dict[str, Any]] = []
        for source_type in ("kettle", "java", "metadata", "system", "ui"):
            file_groups = grouped.get(source_type, {})
            groups.append(
                {
                    "source_type": source_type,
                    "files": [
                        {"file_path": file_path, "failures": file_failures}
                        for file_path, file_failures in sorted(file_groups.items(), key=lambda item: item[0])
                    ],
                }
            )

        return {
            "scan_run": _scan_run_payload(latest),
            "summary": {
                "scan_run_id": latest.id,
                "failure_count": len(failures),
                "file_count": len({failure.file_path for failure in failures}),
                "source_counts": source_counts,
            },
            "groups": groups,
        }

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

        table = db.scalar(
            select(Node).where(Node.type.in_(("table", "data_object", "api_endpoint", "report_file", "menu")), Node.key == table_key)
        )
        if table is None:
            return None

        if table.type == "api_endpoint":
            touched_table_stmt = (
                select(Node)
                .join(Edge, Edge.dst_node_id == Node.id)
                .where(Edge.src_node_id == table.id, Edge.type.in_(("READS", "WRITES")))
                .order_by(Node.name.asc(), Node.id.asc())
            )
            touched_tables = list(db.scalars(touched_table_stmt).all())
            return {
                "table": _serialize_object(table),
                "upstream_tables": [],
                "downstream_tables": [_serialize_object(node) for node in touched_tables],
                "related_objects": self._empty_related_objects(),
            }

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

        table = db.scalar(
            select(Node).where(Node.type.in_(("table", "data_object", "api_endpoint", "report_file", "menu")), Node.key == table_key)
        )
        if table is None:
            return {"table_lineage": None, "items": []}

        if table.type == "api_endpoint":
            table_lineage = self.get_table_lineage(db, table.key)
            return {
                "table_lineage": table_lineage,
                "items": [] if table_lineage is None else [table_lineage],
            }

        upstream_ids = self._collect_directional_table_ids(db, table.id, direction="upstream")
        downstream_ids = self._collect_directional_table_ids(db, table.id, direction="downstream")
        allowed_ids = upstream_ids | downstream_ids | {table.id}
        api_source_table_ids = downstream_ids | {table.id}
        raw_lineages = [
            self.get_table_lineage(db, node.key)
            for node in db.scalars(
                select(Node).where(Node.id.in_(allowed_ids)).order_by(Node.name.asc(), Node.id.asc())
            ).all()
        ]
        api_endpoint_keys = {
            node_key
            for node_key in db.scalars(
                select(Node.key).where(
                    Node.id.in_(self._collect_connected_api_endpoint_ids(db, api_source_table_ids))
                )
            ).all()
        }
        items = self._collect_directional_lineages(
            table.key,
            [lineage for lineage in raw_lineages if lineage is not None],
            terminal_keys=api_endpoint_keys,
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

    def get_field_lineage(self, db: Session, table_key: str) -> dict[str, Any] | None:
        """Return field-level upstream/downstream lineage for one table."""

        table = db.scalar(
            select(Node).where(Node.type.in_(("table", "data_object", "api_endpoint")), Node.key == table_key)
        )
        if table is None:
            return None

        upstream_fields: list[dict[str, Any]] = []
        downstream_fields: list[dict[str, Any]] = []

        upstream_rows = db.execute(
            select(FieldEdge, Node)
            .join(Node, Node.id == FieldEdge.src_node_id)
            .where(FieldEdge.dst_node_id == table.id)
            .order_by(FieldEdge.dst_field.asc(), Node.name.asc(), FieldEdge.src_field.asc())
        ).all()
        for field_edge, src_node in upstream_rows:
            upstream_fields.append(
                {
                    "field": field_edge.dst_field,
                    "source_table": _serialize_object(src_node),
                    "source_field": field_edge.src_field,
                    "is_derived": field_edge.is_derived,
                }
            )

        downstream_rows = db.execute(
            select(FieldEdge, Node)
            .join(Node, Node.id == FieldEdge.dst_node_id)
            .where(FieldEdge.src_node_id == table.id)
            .order_by(FieldEdge.src_field.asc(), Node.name.asc(), FieldEdge.dst_field.asc())
        ).all()
        for field_edge, dst_node in downstream_rows:
            downstream_fields.append(
                {
                    "field": field_edge.src_field,
                    "target_table": _serialize_object(dst_node),
                    "target_field": field_edge.dst_field,
                    "is_derived": field_edge.is_derived,
                }
            )

        return {
            "table": _serialize_object(table),
            "upstream_fields": upstream_fields,
            "downstream_fields": downstream_fields,
        }

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
                if node is None or node.type not in {"table", "data_object", "report_file", "menu"}:
                    continue
                visited.add(node_id)
                next_frontier.add(node_id)
            frontier = next_frontier

        return visited

    def _collect_connected_api_endpoint_ids(self, db: Session, table_ids: set[int]) -> set[int]:
        """Return API endpoints that directly read or write the collected table-like nodes."""

        if not table_ids:
            return set()

        return set(
            db.scalars(
                select(Edge.src_node_id)
                .join(Node, Node.id == Edge.src_node_id)
                .where(
                    Node.type == "api_endpoint",
                    Edge.dst_node_id.in_(table_ids),
                    Edge.type.in_(("READS", "WRITES")),
                )
            ).all()
        )

    def _collect_directional_lineages(
        self,
        current_table_key: str,
        lineages: list[dict[str, Any]],
        *,
        terminal_keys: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Keep only monotonic upstream/downstream paths around the current table."""

        lineage_by_key: dict[str, dict[str, Any]] = {}
        upstream_by_node: dict[str, set[str]] = {}
        downstream_by_node: dict[str, set[str]] = {}
        terminal_keys = terminal_keys or set()

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
        allowed_keys = upstream_reachable | downstream_reachable | {current_table_key} | terminal_keys

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
