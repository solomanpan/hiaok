from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from ...application.model import CreateRole, RoleModel, UpdateRole
from .common import EntityResponse, MetaRequest, MetaUpdateRequest


class RoleCreateRequest(MetaRequest):
    tenant_uuid: str
    role_code: str
    role_name: str
    role_type: Literal[0, 1] = 1

    def to_command(self, org_uuid: str) -> CreateRole:
        return CreateRole(org_uuid=org_uuid, **self.model_dump())


class RoleUpdateRequest(MetaUpdateRequest):
    role_name: str | None = None

    def to_command(self) -> UpdateRole:
        return UpdateRole(**self.model_dump())


class GrantPermissionsRequest(BaseModel):
    permission_uuids: list[str]


class AssignMenusRequest(BaseModel):
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
