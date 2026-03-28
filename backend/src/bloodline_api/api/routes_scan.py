"""Scan pipeline endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from bloodline_api.db import get_db
from bloodline_api.models import ScanRun
from bloodline_api.services.lineage_query import lineage_query_service


router = APIRouter()


class ScanRequest(BaseModel):
    """Payload accepted by the scan endpoint."""

    model_config = ConfigDict(extra="ignore")

    repo_path: str | None = None
    java_source_root: str | None = None
    mysql_dsn: str | None = None


def _scan_run_payload(scan_run: ScanRun | None) -> dict[str, object] | None:
    """Serialize a scan run into the compact JSON shape used by the UI."""

    if scan_run is None:
        return None

    return {
        "id": scan_run.id,
        "status": scan_run.status,
        "started_at": scan_run.started_at,
        "finished_at": scan_run.finished_at,
        "created_at": scan_run.created_at,
    }


@router.post("/scan", status_code=202)
def create_scan(request: ScanRequest | None = None, db: Session = Depends(get_db)) -> dict[str, object]:
    """Run a synchronous MVP scan and return the created scan-run record."""

    scan_run = lineage_query_service.scan_from_inputs(
        db,
        repo_path=None if request is None else request.repo_path,
        java_source_root=None if request is None else request.java_source_root,
        mysql_dsn=None if request is None else request.mysql_dsn,
    )
    return {
        "scan_run_id": scan_run.id,
        "status": scan_run.status,
        "inputs": {} if request is None else request.model_dump(exclude_none=True),
    }


@router.get("/scan-runs/latest")
def latest_scan_run(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return the most recent scan run for progress widgets and status displays."""

    latest = next(iter(lineage_query_service.list_scan_runs(db)), None)
    return {"scan_run": _scan_run_payload(latest)}
