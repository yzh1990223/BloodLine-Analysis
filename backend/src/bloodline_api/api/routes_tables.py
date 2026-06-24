"""Table lineage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from sqlalchemy import select

from bloodline_api.db import get_db
from bloodline_api.models import Edge, Node
from bloodline_api.services.lineage_exporter import build_excel_export, sync_lineage_to_mysql
from bloodline_api.services.lineage_query import lineage_query_service


router = APIRouter()


@router.get("/tables/search")
def search_tables(q: str = Query(default=""), db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    """Search persisted table nodes by key or display name."""

    items = [
        {
            "id": node.id,
            "key": node.key,
            "name": node.name,
            "display_name": (
                node.object_metadata.comment if node.object_metadata is not None and node.object_metadata.comment else node.name
            ),
            "object_type": node.payload.get("object_type", "data_table"),
            "payload": node.payload,
        }
        for node in lineage_query_service.search_tables(db, q)
    ]
    return {"items": items}


@router.get("/analysis/self-loops")
def self_loop_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return aggregated self-loop counts so the frontend can spotlight suspicious tables."""

    return lineage_query_service.get_self_loop_summary(db)


@router.get("/analysis/cycles")
def cycle_group_summary(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return grouped multi-table closed loops for analysis pages."""

    return lineage_query_service.get_cycle_group_summary(db)


@router.get("/tables/{table_key:path}/lineage")
def table_lineage(table_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Return direct lineage neighbors and related objects for one table."""

    lineage = lineage_query_service.get_table_lineage(db, table_key)
    return lineage or {
        "table": None,
        "upstream_tables": [],
        "downstream_tables": [],
        "related_objects": {"jobs": [], "java_modules": [], "api_endpoints": [], "transformations": []},
    }


@router.get("/tables/{table_key:path}/connected-lineage")
def connected_table_lineage(table_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Return the detail-page directional lineage subgraph in one backend round-trip."""

    return lineage_query_service.get_connected_table_lineage(db, table_key)


@router.get("/tables/{table_key:path}/impact")
def table_impact(table_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Return direct lineage plus downstream impact expansion for one table."""

    impact = lineage_query_service.get_table_impact(db, table_key)
    return impact or {
        "table": None,
        "upstream_tables": [],
        "downstream_tables": [],
        "impacted_tables": [],
        "related_objects": {"jobs": [], "java_modules": [], "api_endpoints": [], "transformations": []},
    }


@router.get("/tables/{table_key:path}/field-lineage")
def table_field_lineage(table_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    """Return field-level upstream/downstream lineage for one table."""

    field_lineage = lineage_query_service.get_field_lineage(db, table_key)
    return field_lineage or {
        "table": None,
        "upstream_fields": [],
        "downstream_fields": [],
    }


@router.get("/export/lineage/excel")
def export_lineage_excel(db: Session = Depends(get_db)) -> StreamingResponse:
    """Export table-level lineage to Excel (.xlsx) matching t_relationship columns."""

    excel_bytes = build_excel_export(db)
    return StreamingResponse(
        iter([excel_bytes]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=lineage.xlsx"},
    )


class SyncLineageRequest(BaseModel):
    mysql_dsn: str | None = None


@router.post("/sync/lineage/mysql")
def sync_lineage_mysql(request: SyncLineageRequest, db: Session = Depends(get_db)) -> dict[str, object]:
    """Sync table-level lineage to MySQL t_relationship using the configured DSN."""

    mysql_dsn = request.mysql_dsn or "mysql+pymysql://root:root@127.0.0.1:3306/DM"
    result = sync_lineage_to_mysql(db, mysql_dsn)
    return {
        "success": True,
        "inserted": result["inserted"],
        "message": f"成功同步 {result['inserted']} 条血缘关系到 MySQL t_relationship",
    }


@router.get("/scheduling/lineage")
def scheduling_lineage(
    source: str = Query(default=""),
    target: str = Query(default=""),
    db: Session = Depends(get_db),
) -> dict[str, list[dict[str, object]]]:
    """Return table-level lineage in a scheduling report format with actor attribution."""

    from sqlalchemy.orm import aliased
    Src = aliased(Node)
    Dst = aliased(Node)

    stmt = (
        select(Edge, Src, Dst)
        .join(Src, Edge.src_node_id == Src.id)
        .join(Dst, Edge.dst_node_id == Dst.id)
        .where(Edge.type == "FLOWS_TO")
    )
    if source:
        stmt = stmt.where(Src.name.ilike(f"%{source}%"))
    if target:
        stmt = stmt.where(Dst.name.ilike(f"%{target}%"))
    stmt = stmt.order_by(Src.name.asc(), Dst.name.asc())

    items: list[dict[str, object]] = []
    for edge, src, dst in db.execute(stmt).all():
        payload = dict(edge.payload or {})
        if payload.get("source") == "finereport":
            actors = [{"type": "finereport", "name": dst.name}]
        elif src.type == "api_endpoint" and dst.type == "web_page":
            actors = [{"type": "api", "name": src.name}]
        elif src.type == "report_file" and dst.type == "menu":
            actors = [{"type": "finereport_file", "name": src.name}]
        else:
            reads_actors = select(Edge.src_node_id).where(
                Edge.type == "READS", Edge.dst_node_id == src.id
            )
            writes_actors = select(Edge.src_node_id).where(
                Edge.type == "WRITES", Edge.dst_node_id == dst.id
            )
            actor_stmt = (
                select(Node)
                .where(Node.id.in_(reads_actors), Node.id.in_(writes_actors))
                .order_by(Node.name.asc())
            )
            actors = []
            for actor in db.scalars(actor_stmt).all():
                if actor.type in ("transformation", "job"):
                    actors.append({"type": "kettle", "name": actor.name})
                elif actor.type in ("java_module", "api_endpoint"):
                    actors.append({"type": "java", "name": actor.name})
                else:
                    actors.append({"type": actor.type, "name": actor.name})
        if not actors:
            actors = [{"type": "未知", "name": "-"}]
        for actor in actors:
            items.append(
                {
                    "source_name": src.name,
                    "target_name": dst.name,
                    "actor_type": actor["type"],
                    "actor_name": actor["name"],
                }
            )

    return {"items": items}
