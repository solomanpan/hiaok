from __future__ import annotations

from dataclasses import dataclass, field

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import Role
from ...domain.enum import RoleType
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class RoleModel(EntityModel):
    role_uuid: str
    tenant_uuid: str
    role_code: str
    role_name: str
    role_type: int = RoleType.CUSTOM
    permission_uuids: list[str] = field(default_factory=list)
    menu_uuids: list[str] = field(default_factory=list)

    @classmethod
    def from_domain(cls, r: Role) -> RoleModel:
        return cls(
            **entity_fields(r),
            role_uuid=r.role_uuid,
            tenant_uuid=r.tenant_uuid,
            role_code=r.role_code.value,
            role_name=r.role_name,
            role_type=int(r.role_type),
            permission_uuids=sorted(r.permission_uuids),
            menu_uuids=sorted(r.menu_uuids),
        )

    def to_domain(self) -> Role:
        return Role(
            **entity_kwargs(self),
            role_uuid=self.role_uuid,
            tenant_uuid=self.tenant_uuid,
            role_code=Code(self.role_code),
            role_name=self.role_name,
            role_type=RoleType(self.role_type),
            permission_uuids=frozenset(self.permission_uuids),
            menu_uuids=frozenset(self.menu_uuids),
        )


@dataclass(frozen=True, kw_only=True)
class CreateRole(CreateMeta):
    org_uuid: str
    tenant_uuid: str
    role_code: str
    role_name: str
    role_type: int = RoleType.CUSTOM

    def to_domain(self, uuid: str) -> Result[Role, DomainError]:
        return Role.create(
            self.org_uuid,
            uuid,
            self.tenant_uuid,
            self.role_code,
            self.role_name,
            role_type=RoleType(self.role_type),
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateRole(UpdateMeta):
    role_name: str | None = None

    def apply_to(self, r: Role) -> Result[Role, DomainError]:
        return r.rename(self.role_name).map(self.apply_meta)
