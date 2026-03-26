"""Database engine and session helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from bloodline_api.config import DATABASE_URL, SQLALCHEMY_ECHO


# The MVP keeps a single process-wide engine/session factory pair.
engine = create_engine(DATABASE_URL, echo=SQLALCHEMY_ECHO, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for request handlers and jobs."""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
