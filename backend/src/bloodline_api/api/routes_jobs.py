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
            "id": scan_run.id,
            "status": scan_run.status,
            "started_at": scan_run.started_at,
            "finished_at": scan_run.finished_at,
            "created_at": scan_run.created_at,
        }
        for scan_run in lineage_query_service.list_scan_runs(db)
    ]
    return {"items": items}
