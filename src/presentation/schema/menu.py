from __future__ import annotations

from typing import Literal

from pydantic import Field

from ...application.model import CreateMenu, MenuModel, UpdateMenu
from .common import EntityResponse, MetaRequest, MetaUpdateRequest


class MenuCreateRequest(MetaRequest):
    menu_code: str
    menu_name: str
    menu_type: Literal[0, 1, 2] = 1
    parent_uuid: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    sort_order: int = Field(default=0, ge=0)
    visible: bool = True

    def to_command(self, org_uuid: str) -> CreateMenu:
        return CreateMenu(org_uuid=org_uuid, **self.model_dump())


class MenuUpdateRequest(MetaUpdateRequest):
    menu_name: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    sort_order: int | None = Field(default=None, ge=0)
    visible: bool | None = None

    def to_command(self) -> UpdateMenu:
        return UpdateMenu(**self.model_dump())


class MenuResponse(EntityResponse):
    menu_uuid: str
    menu_code: str
    menu_name: str
    menu_type: int
    parent_uuid: str | None = None
    path: str | None = None
    component: str | None = None
    icon: str | None = None
    sort_order: int
    visible: bool

    @classmethod
    def of(cls, m: MenuModel) -> MenuResponse:
        return cls.model_validate(m)
