"""Scan pipeline endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from bloodline_api.db import get_db
from bloodline_api.models import ScanRun


router = APIRouter()


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    repo_path: str | None = None
    java_source_root: str | None = None
    mysql_dsn: str | None = None


@router.post("/scan", status_code=202)
def create_scan(request: ScanRequest | None = None, db: Session = Depends(get_db)) -> dict[str, object]:
    scan_run = ScanRun(status="queued")
    db.add(scan_run)
    db.commit()
    db.refresh(scan_run)
    return {
        "scan_run_id": scan_run.id,
        "status": scan_run.status,
        "inputs": {} if request is None else request.model_dump(exclude_none=True),
    }
