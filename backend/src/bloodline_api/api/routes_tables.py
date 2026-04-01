"""Table lineage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from bloodline_api.db import get_db
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
