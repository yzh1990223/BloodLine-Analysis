"""Export lineage relationships to the standard t_relationship table.

Supports both table-level and field-level lineage export.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from bloodline_api.models import Edge, FieldEdge, Node, ObjectMetadata

# Target schema for the standard t_relationship table in MySQL.
_TARGET_SCHEMA = "dm"


def _normalize_target_dsn(mysql_dsn: str, default_db: str = _TARGET_SCHEMA) -> str:
    """Ensure the target MySQL DSN points at the lineage database (dm).

    If the configured database name is ``frms`` (used for reading FineReport
    config tables), replace it with ``default_db`` so that ``t_relationship``
    is always read/written in the lineage database without forcing users to
    change their DSN configuration.
    """

    parsed = urlparse(mysql_dsn)
    db_name = (parsed.path or "").lstrip("/") or ""
    if not db_name or db_name.lower() == "frms":
        parsed = parsed._replace(path=f"/{default_db}")
    return urlunparse(parsed)


def _node_metadata(db: Session, node_id: int) -> dict[str, Any]:
    """Fetch node and its metadata for export mapping."""

    node = db.get(Node, node_id)
    if node is None:
        return {}

    metadata = node.object_metadata
    if metadata is not None:
        return {
            "obj_type": metadata.object_kind.upper() if metadata.object_kind else "TABLE",
            "db_name": metadata.database_name or None,
            "schema": metadata.database_name or None,  # Username/Schema mapping
            "obj_enname": metadata.object_name or node.name,
            "obj_chnname": metadata.comment or None,
        }

    # Fallback for nodes without MySQL metadata
    obj_type = "TABLE"
    if node.payload:
        kind = node.payload.get("object_type")
        if kind == "table_view":
            obj_type = "VIEW"
        elif kind == "api_endpoint":
            obj_type = "API"
        elif node.type == "java_module":
            obj_type = "JAVA_MODULE"
        elif node.type == "job":
            obj_type = "JOB"
        elif node.type == "transformation":
            obj_type = "TRANSFORMATION"

    name = node.name
    schema = None
    if "." in name:
        schema, name = name.split(".", 1)

    return {
        "obj_type": obj_type,
        "db_name": None,
        "schema": schema,
        "obj_enname": name,
        "obj_chnname": None,
    }


def create_t_relationship_table(db: Session) -> None:
    """Create the t_relationship table if it does not exist (SQLite-compatible DDL)."""

    ddl = """
    CREATE TABLE IF NOT EXISTS t_relationship (
        key_id INTEGER PRIMARY KEY AUTOINCREMENT,
        src_obj_type VARCHAR(50) NOT NULL,
        src_db_name VARCHAR(100),
        src_schema VARCHAR(100),
        src_obj_enname VARCHAR(500),
        src_obj_chnname VARCHAR(100),
        src_obj_sys VARCHAR(100),
        src_obj_dep VARCHAR(100),
        src_obj_memo VARCHAR(500),
        src_obj_application VARCHAR(500),
        tgt_obj_type VARCHAR(50) NOT NULL,
        tgt_db_name VARCHAR(100),
        tgt_schema VARCHAR(100),
        tgt_obj_enname VARCHAR(500),
        tgt_obj_chnname VARCHAR(100),
        tgt_obj_sys VARCHAR(100),
        tgt_obj_dep VARCHAR(100),
        tgt_obj_memo VARCHAR(100),
        tgt_obj_application VARCHAR(100)
    )
    """
    db.execute(text(ddl))
    db.commit()


def create_t_relationship_table_mysql(db: Session) -> None:
    """Create the t_relationship table if it does not exist (MySQL-compatible DDL).

    If the table already exists, only attempt to widen ``src_obj_enname`` and
    ``tgt_obj_enname`` when they are shorter than 500 characters.  Missing ALTER
    privileges are silently ignored so deployments with a DBA-created table only
    need INSERT permission.
    """

    result = db.execute(text(f"SHOW TABLES FROM `{_TARGET_SCHEMA}` LIKE 't_relationship'"))
    table_exists = result.fetchone() is not None

    if not table_exists:
        ddl = f"""
        CREATE TABLE IF NOT EXISTS `{_TARGET_SCHEMA}`.`t_relationship` (
            key_id INT PRIMARY KEY AUTO_INCREMENT,
            src_obj_type VARCHAR(50) NOT NULL,
            src_db_name VARCHAR(100),
            src_schema VARCHAR(100),
            src_obj_enname VARCHAR(500),
            src_obj_chnname VARCHAR(100),
            src_obj_sys VARCHAR(100),
            src_obj_dep VARCHAR(100),
            src_obj_memo VARCHAR(500),
            src_obj_application VARCHAR(500),
            tgt_obj_type VARCHAR(50) NOT NULL,
            tgt_db_name VARCHAR(100),
            tgt_schema VARCHAR(100),
            tgt_obj_enname VARCHAR(500),
            tgt_obj_chnname VARCHAR(100),
            tgt_obj_sys VARCHAR(100),
            tgt_obj_dep VARCHAR(100),
            tgt_obj_memo VARCHAR(100),
            tgt_obj_application VARCHAR(100)
        )
        """
        db.execute(text(ddl))
        db.commit()
        return

    # Table exists: ensure columns are wide enough, but do not fail if ALTER is denied.
    column_info = db.execute(
        text(f"""
        SELECT COLUMN_NAME, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{_TARGET_SCHEMA}' AND TABLE_NAME = 't_relationship'
        AND COLUMN_NAME IN ('src_obj_enname', 'tgt_obj_enname')
        """)
    ).mappings()
    lengths = {row["COLUMN_NAME"]: row["CHARACTER_MAXIMUM_LENGTH"] for row in column_info}

    if lengths.get("src_obj_enname", 0) is not None and (lengths.get("src_obj_enname") or 0) < 500:
        try:
            db.execute(text(f"ALTER TABLE `{_TARGET_SCHEMA}`.`t_relationship` MODIFY COLUMN src_obj_enname VARCHAR(500)"))
        except Exception:
            pass  # DBA-managed table may lack ALTER privilege.

    if lengths.get("tgt_obj_enname", 0) is not None and (lengths.get("tgt_obj_enname") or 0) < 500:
        try:
            db.execute(text(f"ALTER TABLE `{_TARGET_SCHEMA}`.`t_relationship` MODIFY COLUMN tgt_obj_enname VARCHAR(500)"))
        except Exception:
            pass

    db.commit()


def export_table_lineage_to_t_relationship(db: Session) -> int:
    """Export table-level FLOWS_TO edges to t_relationship.

    Returns the number of rows inserted.
    """

    create_t_relationship_table(db)

    flows = db.query(Edge).filter(Edge.type == "FLOWS_TO").all()
    inserted = 0

    for edge in flows:
        src_meta = _node_metadata(db, edge.src_node_id)
        tgt_meta = _node_metadata(db, edge.dst_node_id)

        if not src_meta or not tgt_meta:
            continue

        db.execute(
            text("""
            INSERT INTO t_relationship (
                src_obj_type, src_db_name, src_schema, src_obj_enname, src_obj_chnname,
                src_obj_sys, src_obj_dep, src_obj_memo, src_obj_application,
                tgt_obj_type, tgt_db_name, tgt_schema, tgt_obj_enname, tgt_obj_chnname,
                tgt_obj_sys, tgt_obj_dep, tgt_obj_memo, tgt_obj_application
            ) VALUES (
                :src_obj_type, :src_db_name, :src_schema, :src_obj_enname, :src_obj_chnname,
                :src_obj_sys, :src_obj_dep, :src_obj_memo, :src_obj_application,
                :tgt_obj_type, :tgt_db_name, :tgt_schema, :tgt_obj_enname, :tgt_obj_chnname,
                :tgt_obj_sys, :tgt_obj_dep, :tgt_obj_memo, :tgt_obj_application
            )
            """),
            {
                "src_obj_type": src_meta["obj_type"],
                "src_db_name": src_meta["db_name"],
                "src_schema": src_meta["schema"],
                "src_obj_enname": src_meta["obj_enname"],
                "src_obj_chnname": src_meta["obj_chnname"],
                "src_obj_sys": None,
                "src_obj_dep": None,
                "src_obj_memo": None,
                "src_obj_application": None,
                "tgt_obj_type": tgt_meta["obj_type"],
                "tgt_db_name": tgt_meta["db_name"],
                "tgt_schema": tgt_meta["schema"],
                "tgt_obj_enname": tgt_meta["obj_enname"],
                "tgt_obj_chnname": tgt_meta["obj_chnname"],
                "tgt_obj_sys": None,
                "tgt_obj_dep": None,
                "tgt_obj_memo": None,
                "tgt_obj_application": None,
            },
        )
        inserted += 1

    db.commit()
    return inserted


def export_field_lineage_to_t_relationship(db: Session) -> int:
    """Export field-level edges to t_relationship with obj_type='COLUMN'.

    The field name is appended to the table name as 'table.column'.
    Returns the number of rows inserted.
    """

    create_t_relationship_table(db)

    field_edges = db.query(FieldEdge).all()
    inserted = 0

    for edge in field_edges:
        src_meta = _node_metadata(db, edge.src_node_id)
        tgt_meta = _node_metadata(db, edge.dst_node_id)

        if not src_meta or not tgt_meta:
            continue

        src_enname = f"{src_meta['obj_enname']}.{edge.src_field}"
        tgt_enname = f"{tgt_meta['obj_enname']}.{edge.dst_field}"

        db.execute(
            text("""
            INSERT INTO t_relationship (
                src_obj_type, src_db_name, src_schema, src_obj_enname, src_obj_chnname,
                src_obj_sys, src_obj_dep, src_obj_memo, src_obj_application,
                tgt_obj_type, tgt_db_name, tgt_schema, tgt_obj_enname, tgt_obj_chnname,
                tgt_obj_sys, tgt_obj_dep, tgt_obj_memo, tgt_obj_application
            ) VALUES (
                :src_obj_type, :src_db_name, :src_schema, :src_obj_enname, :src_obj_chnname,
                :src_obj_sys, :src_obj_dep, :src_obj_memo, :src_obj_application,
                :tgt_obj_type, :tgt_db_name, :tgt_schema, :tgt_obj_enname, :tgt_obj_chnname,
                :tgt_obj_sys, :tgt_obj_dep, :tgt_obj_memo, :tgt_obj_application
            )
            """),
            {
                "src_obj_type": "COLUMN",
                "src_db_name": src_meta["db_name"],
                "src_schema": src_meta["schema"],
                "src_obj_enname": src_enname,
                "src_obj_chnname": src_meta["obj_chnname"],
                "src_obj_sys": None,
                "src_obj_dep": None,
                "src_obj_memo": None,
                "src_obj_application": None,
                "tgt_obj_type": "COLUMN",
                "tgt_db_name": tgt_meta["db_name"],
                "tgt_schema": tgt_meta["schema"],
                "tgt_obj_enname": tgt_enname,
                "tgt_obj_chnname": tgt_meta["obj_chnname"],
                "tgt_obj_sys": None,
                "tgt_obj_dep": None,
                "tgt_obj_memo": None,
                "tgt_obj_application": None,
            },
        )
        inserted += 1

    db.commit()
    return inserted


def export_all_lineage_to_t_relationship(db: Session) -> dict[str, int]:
    """Export both table-level and field-level lineage to t_relationship.

    Returns a summary dict with counts.
    """

    table_count = export_table_lineage_to_t_relationship(db)
    field_count = export_field_lineage_to_t_relationship(db)

    return {
        "table_level": table_count,
        "field_level": field_count,
        "total": table_count + field_count,
    }


def sync_lineage_to_mysql(db: Session, mysql_dsn: str) -> dict[str, int]:
    """Sync table-level FLOWS_TO edges from local SQLite to MySQL t_relationship.

    Args:
        db: Local SQLite session (reads Edge/Node data).
        mysql_dsn: SQLAlchemy DSN for the target MySQL instance.

    Returns:
        {"inserted": N} summary.
    """

    target_dsn = _normalize_target_dsn(mysql_dsn)
    mysql_engine = create_engine(target_dsn, future=True, pool_pre_ping=True)
    MySQLSession = sessionmaker(bind=mysql_engine, autoflush=False, autocommit=False, future=True)
    mysql_db = MySQLSession()

    try:
        create_t_relationship_table_mysql(mysql_db)

        flows = db.query(Edge).filter(Edge.type == "FLOWS_TO").all()
        inserted = 0

        for edge in flows:
            src_meta = _node_metadata(db, edge.src_node_id)
            tgt_meta = _node_metadata(db, edge.dst_node_id)

            if not src_meta or not tgt_meta:
                continue

            mysql_db.execute(
                text("""
                INSERT INTO `{_TARGET_SCHEMA}`.`t_relationship` (
                    src_obj_type, src_db_name, src_schema, src_obj_enname, src_obj_chnname,
                    src_obj_sys, src_obj_dep, src_obj_memo, src_obj_application,
                    tgt_obj_type, tgt_db_name, tgt_schema, tgt_obj_enname, tgt_obj_chnname,
                    tgt_obj_sys, tgt_obj_dep, tgt_obj_memo, tgt_obj_application
                ) VALUES (
                    :src_obj_type, :src_db_name, :src_schema, :src_obj_enname, :src_obj_chnname,
                    :src_obj_sys, :src_obj_dep, :src_obj_memo, :src_obj_application,
                    :tgt_obj_type, :tgt_db_name, :tgt_schema, :tgt_obj_enname, :tgt_obj_chnname,
                    :tgt_obj_sys, :tgt_obj_dep, :tgt_obj_memo, :tgt_obj_application
                )
                """),
                {
                    "src_obj_type": src_meta["obj_type"],
                    "src_db_name": src_meta["db_name"],
                    "src_schema": src_meta["schema"],
                    "src_obj_enname": (src_meta["obj_enname"] or "")[:500],
                    "src_obj_chnname": src_meta["obj_chnname"],
                    "src_obj_sys": None,
                    "src_obj_dep": None,
                    "src_obj_memo": None,
                    "src_obj_application": None,
                    "tgt_obj_type": tgt_meta["obj_type"],
                    "tgt_db_name": tgt_meta["db_name"],
                    "tgt_schema": tgt_meta["schema"],
                    "tgt_obj_enname": (tgt_meta["obj_enname"] or "")[:500],
                    "tgt_obj_chnname": tgt_meta["obj_chnname"],
                    "tgt_obj_sys": None,
                    "tgt_obj_dep": None,
                    "tgt_obj_memo": None,
                    "tgt_obj_application": None,
                },
            )
            inserted += 1

        mysql_db.commit()
        return {"inserted": inserted}
    finally:
        mysql_db.close()
        mysql_engine.dispose()


def build_excel_export(db: Session, mysql_dsn: str | None = None) -> bytes:
    """Build an Excel workbook with table-level lineage data.

    If ``mysql_dsn`` is provided, data is read from the remote MySQL
    ``t_relationship`` table. Otherwise the local SQLite ``Edge`` table is used.

    Returns the raw bytes of the .xlsx file.
    """

    from io import BytesIO
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "血缘关系"

    headers = [
        "src_obj_type", "src_db_name", "src_schema", "src_obj_enname", "src_obj_chnname",
        "src_obj_sys", "src_obj_dep", "src_obj_memo", "src_obj_application",
        "tgt_obj_type", "tgt_db_name", "tgt_schema", "tgt_obj_enname", "tgt_obj_chnname",
        "tgt_obj_sys", "tgt_obj_dep", "tgt_obj_memo", "tgt_obj_application",
    ]
    ws.append(headers)

    if mysql_dsn:
        # Read from the synced MySQL t_relationship table.
        target_dsn = _normalize_target_dsn(mysql_dsn)
        mysql_engine = create_engine(target_dsn, future=True, pool_pre_ping=True)
        MySQLSession = sessionmaker(bind=mysql_engine, autoflush=False, autocommit=False, future=True)
        mysql_db = MySQLSession()
        try:
            rows = mysql_db.execute(
                text("""
                    SELECT
                        src_obj_type, src_db_name, src_schema, src_obj_enname, src_obj_chnname,
                        src_obj_sys, src_obj_dep, src_obj_memo, src_obj_application,
                        tgt_obj_type, tgt_db_name, tgt_schema, tgt_obj_enname, tgt_obj_chnname,
                        tgt_obj_sys, tgt_obj_dep, tgt_obj_memo, tgt_obj_application
                    FROM `{_TARGET_SCHEMA}`.`t_relationship`
                """)
            ).mappings()
            for row in rows:
                ws.append([row[h] or "" for h in headers])
        finally:
            mysql_db.close()
            mysql_engine.dispose()
    else:
        # Fall back to local SQLite Edge data.
        flows = db.query(Edge).filter(Edge.type == "FLOWS_TO").all()
        for edge in flows:
            src_meta = _node_metadata(db, edge.src_node_id)
            tgt_meta = _node_metadata(db, edge.dst_node_id)
            if not src_meta or not tgt_meta:
                continue

            ws.append([
                src_meta["obj_type"],
                src_meta["db_name"] or "",
                src_meta["schema"] or "",
                src_meta["obj_enname"] or "",
                src_meta["obj_chnname"] or "",
                "", "", "", "",  # sys, dep, memo, application
                tgt_meta["obj_type"],
                tgt_meta["db_name"] or "",
                tgt_meta["schema"] or "",
                tgt_meta["obj_enname"] or "",
                tgt_meta["obj_chnname"] or "",
                "", "", "", "",  # sys, dep, memo, application
            ])

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()
