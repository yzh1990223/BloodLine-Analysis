"""Job and scan-run endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bloodline_api.db import get_db
from bloodline_api.services.lineage_query import lineage_query_service


router = APIRouter()


@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)) -> dict[str, list[dict[str, object]]]:
    items = [
        {
            "id": job_node.id,
            "key": job_node.key,
            "name": job_node.name,
        }
        for job_node in lineage_query_service.list_jobs(db)
    ]
    return {"items": items}


@router.get("/jobs/{job_key:path}")
def job_detail(job_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    detail = lineage_query_service.get_job_detail(db, job_key)
    return detail or {"id": None, "key": job_key, "name": None, "transformations": [], "tables": []}


@router.get("/java-modules/{module_key:path}")
def java_module_detail(module_key: str, db: Session = Depends(get_db)) -> dict[str, object]:
    detail = lineage_query_service.get_java_module_detail(db, module_key)
    return detail or {
        "id": None,
        "key": module_key,
        "name": None,
        "read_tables": [],
        "write_tables": [],
    }
