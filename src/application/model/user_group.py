from __future__ import annotations

from dataclasses import dataclass

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import UserGroup
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class UserGroupModel(EntityModel):
    group_uuid: str
    tenant_uuid: str
    group_code: str
    group_name: str
    parent_group_uuid: str | None = None
    sort_order: int = 0

    @classmethod
    def from_domain(cls, g: UserGroup) -> UserGroupModel:
        return cls(
            **entity_fields(g),
            group_uuid=g.group_uuid,
            tenant_uuid=g.tenant_uuid,
            group_code=g.group_code.value,
            group_name=g.group_name,
            parent_group_uuid=g.parent_group_uuid,
            sort_order=g.sort_order,
        )

    def to_domain(self) -> UserGroup:
        return UserGroup(
            **entity_kwargs(self),
            group_uuid=self.group_uuid,
            tenant_uuid=self.tenant_uuid,
            group_code=Code(self.group_code),
            group_name=self.group_name,
            parent_group_uuid=self.parent_group_uuid,
            sort_order=self.sort_order,
        )


@dataclass(frozen=True, kw_only=True)
class CreateUserGroup(CreateMeta):
    org_uuid: str
    tenant_uuid: str
    group_code: str
    group_name: str
    parent_group_uuid: str | None = None
    sort_order: int = 0

    def to_domain(self, uuid: str) -> Result[UserGroup, DomainError]:
        return UserGroup.create(
            self.org_uuid,
            uuid,
            self.tenant_uuid,
            self.group_code,
            self.group_name,
            parent_group_uuid=self.parent_group_uuid,
            sort_order=self.sort_order,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateUserGroup(UpdateMeta):
    group_name: str | None = None
    sort_order: int | None = None

    def apply_to(self, g: UserGroup) -> Result[UserGroup, DomainError]:
        return g.update(group_name=self.group_name, sort_order=self.sort_order).map(self.apply_meta)
