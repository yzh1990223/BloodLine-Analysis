"""Table lineage endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from bloodline_api.db import get_db
from bloodline_api.services.lineage_query import lineage_query_service


router = APIRouter()


@router.get("/tables/search")
def search_tables(q: str = Query(default=""), db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    items = [
        {"id": node.id, "key": node.key, "name": node.name}
        for node in lineage_query_service.search_tables(db, q)
    ]
    return {"items": items}


@router.get("/tables/{table_key:path}/lineage")
def table_lineage(table_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    lineage = lineage_query_service.get_table_lineage(db, table_key)
    return lineage or {
        "table": None,
        "upstream_tables": [],
        "downstream_tables": [],
        "related_objects": {"jobs": [], "java_modules": [], "transformations": []},
    }


@router.get("/tables/{table_key:path}/impact")
def table_impact(table_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    impact = lineage_query_service.get_table_impact(db, table_key)
    return impact or {
        "table": None,
        "upstream_tables": [],
        "downstream_tables": [],
        "impacted_tables": [],
        "related_objects": {"jobs": [], "java_modules": [], "transformations": []},
    }
