"""Pydantic schemas used by the API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    """Base schema configured for SQLAlchemy model serialization."""

    model_config = ConfigDict(from_attributes=True)


class ScanRunBase(ApiModel):
    """Shared scan-run fields used across create/read variants."""

    status: str = "pending"


class ScanRunCreate(ScanRunBase):
    """Schema for creating scan-run records."""

    pass


class ScanRunRead(ScanRunBase):
    """Schema returned when a scan-run record is serialized."""

    id: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class NodeBase(ApiModel):
    """Shared node fields for the persisted lineage graph."""

    type: str
    key: str
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class NodeCreate(NodeBase):
    """Schema for creating lineage graph nodes."""

    pass


class NodeRead(NodeBase):
    """Schema returned when a lineage graph node is serialized."""

    id: int
    created_at: datetime | None = None


class EdgeBase(ApiModel):
    """Shared edge fields for persisted lineage relationships."""

    type: str
    src_node_id: int
    dst_node_id: int
    is_derived: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class EdgeCreate(EdgeBase):
    """Schema for creating lineage graph edges."""

    pass


class EdgeRead(EdgeBase):
    """Schema returned when a lineage edge is serialized."""

    id: int
    created_at: datetime | None = None
