"""Shared request/response DTO pieces."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ...application.model import TreeModel
from ...domain.repository import Page


class MetaRequest(BaseModel):
    description: str | None = Field(default=None, max_length=512)
    remark: str | None = Field(default=None, max_length=255)


class MetaUpdateRequest(MetaRequest):
    state: Literal[0, 1] | None = Field(default=None, description="0: enabled, 1: disabled")


class EntityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    org_uuid: str
    description: str | None = None
    remark: str | None = None
    state: int
    create_time: datetime | None = None
    update_time: datetime | None = None
    opr: str | None = None


class PageResponse[T](BaseModel):
    items: list[T]
    total: int
    offset: int
    limit: int

    @classmethod
    def of[M](cls, page: Page[M], to_item: Callable[[M], T]) -> PageResponse[T]:
        return cls(items=[to_item(i) for i in page.items], total=page.total, offset=page.offset, limit=page.limit)


class TreeNodeResponse[T](BaseModel):
    item: T
    children: list[TreeNodeResponse[T]] = Field(default_factory=list)

    @classmethod
    def of[M](cls, node: TreeModel[M], to_item: Callable[[M], T]) -> TreeNodeResponse[T]:
        return cls(item=to_item(node.item), children=[cls.of(c, to_item) for c in node.children])


class ErrorResponse(BaseModel):
    code: str
    message: str


class MoveRequest(BaseModel):
    parent_uuid: str | None = Field(default=None, description="null = move to root")
