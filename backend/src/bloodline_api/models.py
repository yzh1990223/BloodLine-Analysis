"""SQLAlchemy models for scans, lineage nodes, and edges."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for the persistence model."""


class ScanRun(Base):
    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    nodes: Mapped[list["Node"]] = relationship(back_populates="scan_run", cascade="all, delete-orphan")
    edges: Mapped[list["Edge"]] = relationship(back_populates="scan_run", cascade="all, delete-orphan")


class Node(Base):
    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_run_id: Mapped[int | None] = mapped_column(ForeignKey("scan_runs.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scan_run: Mapped[ScanRun | None] = relationship(back_populates="nodes")
    outgoing_edges: Mapped[list["Edge"]] = relationship(
        back_populates="source_node",
        foreign_keys="Edge.src_node_id",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["Edge"]] = relationship(
        back_populates="target_node",
        foreign_keys="Edge.dst_node_id",
        cascade="all, delete-orphan",
    )


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_run_id: Mapped[int | None] = mapped_column(ForeignKey("scan_runs.id"), nullable=True, index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    src_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    dst_node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False, index=True)
    is_derived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    scan_run: Mapped[ScanRun | None] = relationship(back_populates="edges")
    source_node: Mapped[Node] = relationship(back_populates="outgoing_edges", foreign_keys=[src_node_id])
    target_node: Mapped[Node] = relationship(back_populates="incoming_edges", foreign_keys=[dst_node_id])
