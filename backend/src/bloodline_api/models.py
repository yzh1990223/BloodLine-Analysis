"""SQLAlchemy models for scans, lineage nodes, edges, and metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base for the persistence model."""


class ScanRun(Base):
    """One execution of the file-driven lineage scan pipeline."""

    __tablename__ = "scan_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    failures: Mapped[list["ScanFailure"]] = relationship(
        back_populates="scan_run",
        cascade="all, delete-orphan",
        order_by="ScanFailure.id",
    )


class Node(Base):
    """A persisted graph node such as a table, job, transformation, or module."""

    __tablename__ = "nodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    outgoing_edges: Mapped[list["Edge"]] = relationship(
        back_populates="source_node",
        foreign_keys="Edge.src_node_id",
    )
    incoming_edges: Mapped[list["Edge"]] = relationship(
        back_populates="target_node",
        foreign_keys="Edge.dst_node_id",
    )
    object_metadata: Mapped["ObjectMetadata | None"] = relationship(
        back_populates="node",
        cascade="all, delete-orphan",
        uselist=False,
    )


class Edge(Base):
    """A persisted graph edge connecting two nodes in the lineage graph."""

    __tablename__ = "edges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
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
    source_node: Mapped[Node] = relationship(back_populates="outgoing_edges", foreign_keys=[src_node_id])
    target_node: Mapped[Node] = relationship(back_populates="incoming_edges", foreign_keys=[dst_node_id])


class ObjectMetadata(Base):
    """Latest metadata snapshot associated with one table or view node."""

    __tablename__ = "object_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[int] = mapped_column(ForeignKey("nodes.id"), nullable=False, unique=True, index=True)
    database_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    object_name: Mapped[str] = mapped_column(String(255), nullable=False)
    object_kind: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    view_definition: Mapped[str | None] = mapped_column(String, nullable=True)
    view_parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="not_applicable")
    view_parse_error: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    metadata_source: Mapped[str] = mapped_column(String(64), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    node: Mapped[Node] = relationship(back_populates="object_metadata")
    columns: Mapped[list["ObjectMetadataColumn"]] = relationship(
        back_populates="object_metadata",
        cascade="all, delete-orphan",
        order_by="ObjectMetadataColumn.ordinal_position",
    )


class ObjectMetadataColumn(Base):
    """Column metadata belonging to one latest object metadata row."""

    __tablename__ = "object_metadata_columns"
    __table_args__ = (
        UniqueConstraint("metadata_id", "column_name", name="uq_object_metadata_columns_metadata_id_column_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    metadata_id: Mapped[int] = mapped_column(
        ForeignKey("object_metadata.id"),
        nullable=False,
        index=True,
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(255), nullable=False)
    ordinal_position: Mapped[int] = mapped_column(Integer, nullable=False)
    is_nullable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    column_comment: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    object_metadata: Mapped[ObjectMetadata] = relationship(back_populates="columns")


class ScanFailure(Base):
    """A persisted failure captured during one scan run."""

    __tablename__ = "scan_failures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_run_id: Mapped[int] = mapped_column(ForeignKey("scan_runs.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False, index=True)
    failure_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(2048), nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    sql_snippet: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    scan_run: Mapped[ScanRun] = relationship(back_populates="failures")
