"""Application configuration for the BloodLine API."""

from __future__ import annotations

import os


# Default to a local SQLite database so the MVP can run without extra infra.
DATABASE_URL = os.getenv(
    "BLOODLINE_DATABASE_URL",
    "sqlite+pysqlite:///./bloodline.db",
)
# This flag is primarily useful when debugging generated SQL and session behavior.
SQLALCHEMY_ECHO = os.getenv("BLOODLINE_SQLALCHEMY_ECHO", "false").lower() == "true"
