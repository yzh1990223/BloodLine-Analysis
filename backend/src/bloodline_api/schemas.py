"""Pydantic schemas used by the API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ScanRunBase(ApiModel):
    status: str = "pending"


class ScanRunCreate(ScanRunBase):
    pass


class ScanRunRead(ScanRunBase):
    id: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime | None = None


class NodeBase(ApiModel):
    type: str
    key: str
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)


class NodeCreate(NodeBase):
    pass


class NodeRead(NodeBase):
    id: int
    created_at: datetime | None = None


class EdgeBase(ApiModel):
    type: str
    src_node_id: int
    dst_node_id: int
    is_derived: bool = False
    payload: dict[str, Any] = Field(default_factory=dict)


class EdgeCreate(EdgeBase):
    pass


class EdgeRead(EdgeBase):
    id: int
    created_at: datetime | None = None
