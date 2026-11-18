"""Shared request/response DTO pieces."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from ...application.model import TreeModel
from ...domain.repository import Page, PageQuery


class ApiModel(BaseModel):
    """Base of every DTO: camelCase on the wire (``orgUuid``), snake_case in Python (``org_uuid``)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


class OrgScoped(ApiModel):
    """Every call except organization provisioning/listing happens inside one organization."""

    org_uuid: str = Field(..., examples=["org-1"])


class Keyed(OrgScoped):
    """Targets one existing resource of the organization (``uuid`` = that resource's uuid)."""

    uuid: str = Field(..., examples=["a1b2c3"])


class PageRequest(ApiModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=200)

    @property
    def query(self) -> PageQuery:
        return PageQuery(self.offset, self.limit)


class OrgPageRequest(OrgScoped, PageRequest):
    pass


class MetaRequest(ApiModel):
    description: str | None = Field(default=None, max_length=512)
    remark: str | None = Field(default=None, max_length=255)


class MetaUpdateRequest(MetaRequest):
    state: Literal[0, 1] | None = Field(default=None, description="0: enabled, 1: disabled")

    def patch(self) -> dict[str, Any]:
        """The fields to change, without the key fields (``orgUuid`` / ``uuid``) that locate the resource."""
        return self.model_dump(exclude={"org_uuid", "uuid"})


class EntityResponse(ApiModel):
    org_uuid: str
    description: str | None = None
    remark: str | None = None
    state: int
    create_time: datetime | None = None
    update_time: datetime | None = None
    opr: str | None = None


class PageResponse[T](ApiModel):
    items: list[T]
    total: int
    offset: int
    limit: int

    @classmethod
    def of[M](cls, page: Page[M], to_item: Callable[[M], T]) -> PageResponse[T]:
        return cls(items=[to_item(i) for i in page.items], total=page.total, offset=page.offset, limit=page.limit)


class TreeNodeResponse[T](ApiModel):
    item: T
    children: list[TreeNodeResponse[T]] = Field(default_factory=list)

    @classmethod
    def of[M](cls, node: TreeModel[M], to_item: Callable[[M], T]) -> TreeNodeResponse[T]:
        return cls(item=to_item(node.item), children=[cls.of(c, to_item) for c in node.children])


class MoveRequest(Keyed):
    parent_uuid: str | None = Field(default=None, description="null = move to root")
