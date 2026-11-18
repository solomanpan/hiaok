from __future__ import annotations

from typing import Literal

from pydantic import Field

from ...application.model import CreatePermission, PermissionModel, UpdatePermission
from .common import EntityResponse, Keyed, MetaRequest, MetaUpdateRequest, OrgScoped


class PermissionCreateRequest(OrgScoped, MetaRequest):
    perm_code: str = Field(..., examples=["project:create"])
    perm_name: str
    perm_type: Literal[0, 1, 2] = 0
    resource: str | None = None
    action: str | None = None
    menu_uuid: str | None = None

    def to_command(self) -> CreatePermission:
        return CreatePermission(**self.model_dump())


class PermissionUpdateRequest(Keyed, MetaUpdateRequest):
    perm_name: str | None = None
    menu_uuid: str | None = None

    def to_command(self) -> UpdatePermission:
        return UpdatePermission(**self.patch())


class PermissionResponse(EntityResponse):
    permission_uuid: str
    perm_code: str
    perm_name: str
    perm_type: int
    resource: str | None = None
    action: str | None = None
    menu_uuid: str | None = None

    @classmethod
    def of(cls, m: PermissionModel) -> PermissionResponse:
        return cls.model_validate(m)
