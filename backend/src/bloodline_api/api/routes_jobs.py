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
