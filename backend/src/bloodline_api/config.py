"""Application configuration for the BloodLine API."""

from __future__ import annotations

import os


DATABASE_URL = os.getenv(
    "BLOODLINE_DATABASE_URL",
    "sqlite+pysqlite:///./bloodline.db",
)
SQLALCHEMY_ECHO = os.getenv("BLOODLINE_SQLALCHEMY_ECHO", "false").lower() == "true"
