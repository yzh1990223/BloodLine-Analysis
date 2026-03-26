"""FastAPI application entrypoint for the BloodLine API."""

from __future__ import annotations

from fastapi import FastAPI

from bloodline_api.api.routes_jobs import router as jobs_router
from bloodline_api.api.routes_scan import router as scan_router
from bloodline_api.api.routes_tables import router as tables_router


app = FastAPI(title="BloodLine API")
app.include_router(scan_router, prefix="/api")
app.include_router(tables_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
