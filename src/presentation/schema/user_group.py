from __future__ import annotations

from pydantic import Field

from ...application.model import CreateUserGroup, UpdateUserGroup, UserGroupModel
from .common import EntityResponse, Keyed, MetaRequest, MetaUpdateRequest, OrgScoped


class UserGroupCreateRequest(OrgScoped, MetaRequest):
    tenant_uuid: str
    group_code: str
    group_name: str
    parent_group_uuid: str | None = None
    sort_order: int = Field(default=0, ge=0)

    def to_command(self) -> CreateUserGroup:
        return CreateUserGroup(**self.model_dump())


class UserGroupUpdateRequest(Keyed, MetaUpdateRequest):
    group_name: str | None = None
    sort_order: int | None = Field(default=None, ge=0)

    def to_command(self) -> UpdateUserGroup:
        return UpdateUserGroup(**self.patch())


class UserGroupResponse(EntityResponse):
    group_uuid: str
    tenant_uuid: str
    group_code: str
    group_name: str
    parent_group_uuid: str | None = None
    sort_order: int

    @classmethod
    def of(cls, m: UserGroupModel) -> UserGroupResponse:
        return cls.model_validate(m)
