"""Scan pipeline endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from bloodline_api.connectors.mysql_metadata import MySQLMetadataConnectionError
from bloodline_api.db import get_db
from bloodline_api.models import ScanRun
from bloodline_api.services.lineage_query import lineage_query_service


router = APIRouter()


class ScanRequest(BaseModel):
    """Payload accepted by the scan endpoint."""

    model_config = ConfigDict(extra="ignore")

    repo_path: str | None = None
    repo_paths: list[str] | None = None
    java_source_root: str | None = None
    java_source_roots: list[str] | None = None
    mysql_dsn: str | None = None
    metadata_databases: list[str] | None = None


def _normalized_scan_inputs(request: ScanRequest | None) -> dict[str, object]:
    """Normalize one scan request into the persisted non-empty inputs shape."""

    if request is None:
        return {}

    inputs: dict[str, object] = {}
    normalized_repo_paths = []
    if request.repo_paths:
        normalized_repo_paths.extend(item.strip() for item in request.repo_paths if item.strip())
    if request.repo_path and request.repo_path.strip():
        normalized_repo_paths.append(request.repo_path.strip())
    if normalized_repo_paths:
        deduped_repo_paths = list(dict.fromkeys(normalized_repo_paths))
        inputs["repo_paths"] = deduped_repo_paths
        inputs["repo_path"] = deduped_repo_paths[0]

    normalized_java_roots = []
    if request.java_source_roots:
        normalized_java_roots.extend(item.strip() for item in request.java_source_roots if item.strip())
    if request.java_source_root and request.java_source_root.strip():
        normalized_java_roots.append(request.java_source_root.strip())
    if normalized_java_roots:
        deduped_java_roots = list(dict.fromkeys(normalized_java_roots))
        inputs["java_source_roots"] = deduped_java_roots
        inputs["java_source_root"] = deduped_java_roots[0]

    if request.mysql_dsn and request.mysql_dsn.strip():
        inputs["mysql_dsn"] = request.mysql_dsn.strip()
    if request.metadata_databases:
        normalized_databases = [item.strip() for item in request.metadata_databases if item.strip()]
        if normalized_databases:
            inputs["metadata_databases"] = normalized_databases
    return inputs


def _scan_run_payload(scan_run: ScanRun | None) -> dict[str, object] | None:
    """Serialize a scan run into the compact JSON shape used by the UI."""

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


@router.post("/scan", status_code=202)
def create_scan(request: ScanRequest | None = None, db: Session = Depends(get_db)) -> dict[str, object]:
    """Run a synchronous MVP scan and return the created scan-run record."""

    normalized_inputs = _normalized_scan_inputs(request)
    try:
        scan_run = lineage_query_service.scan_from_inputs(
            db,
            repo_path=normalized_inputs.get("repo_path"),
            repo_paths=normalized_inputs.get("repo_paths"),
            java_source_root=normalized_inputs.get("java_source_root"),
            java_source_roots=normalized_inputs.get("java_source_roots"),
            mysql_dsn=normalized_inputs.get("mysql_dsn"),
            metadata_databases=normalized_inputs.get("metadata_databases"),
            inputs=normalized_inputs,
        )
    except MySQLMetadataConnectionError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "scan_run_id": scan_run.id,
        "status": scan_run.status,
        "inputs": scan_run.inputs,
    }


@router.get("/scan-runs/latest")
def latest_scan_run(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return the most recent scan run for progress widgets and status displays."""

    latest = next(iter(lineage_query_service.list_scan_runs(db)), None)
    return {"scan_run": _scan_run_payload(latest)}


@router.get("/scan-runs/latest/failures")
def latest_scan_failures(db: Session = Depends(get_db)) -> dict[str, object]:
    """Return the most recent scan failures grouped by source and file."""

    return lineage_query_service.get_latest_scan_failures(db)
