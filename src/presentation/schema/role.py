from __future__ import annotations

from typing import Literal

from ...application.model import CreateRole, RoleModel, UpdateRole
from .common import EntityResponse, Keyed, MetaRequest, MetaUpdateRequest, OrgScoped


class RoleCreateRequest(OrgScoped, MetaRequest):
    tenant_uuid: str
    role_code: str
    role_name: str
    role_type: Literal[0, 1] = 1

    def to_command(self) -> CreateRole:
        return CreateRole(**self.model_dump())


class RoleUpdateRequest(Keyed, MetaUpdateRequest):
    role_name: str | None = None

    def to_command(self) -> UpdateRole:
        return UpdateRole(**self.patch())


class GrantPermissionsRequest(Keyed):
    permission_uuids: list[str]


class AssignMenusRequest(Keyed):
    menu_uuids: list[str]


class RoleResponse(EntityResponse):
    role_uuid: str
    tenant_uuid: str
    role_code: str
    role_name: str
    role_type: int
    permission_uuids: list[str]
    menu_uuids: list[str]

    @classmethod
    def of(cls, m: RoleModel) -> RoleResponse:
        return cls.model_validate(m)
