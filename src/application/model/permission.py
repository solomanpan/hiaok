from __future__ import annotations

from dataclasses import dataclass

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import Permission
from ...domain.enum import PermType
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class PermissionModel(EntityModel):
    permission_uuid: str
    perm_code: str
    perm_name: str
    perm_type: int = PermType.API
    resource: str | None = None
    action: str | None = None
    menu_uuid: str | None = None

    @classmethod
    def from_domain(cls, p: Permission) -> PermissionModel:
        return cls(
            **entity_fields(p),
            permission_uuid=p.permission_uuid,
            perm_code=p.perm_code.value,
            perm_name=p.perm_name,
            perm_type=int(p.perm_type),
            resource=p.resource,
            action=p.action,
            menu_uuid=p.menu_uuid,
        )

    def to_domain(self) -> Permission:
        return Permission(
            **entity_kwargs(self),
            permission_uuid=self.permission_uuid,
            perm_code=Code(self.perm_code),
            perm_name=self.perm_name,
            perm_type=PermType(self.perm_type),
            resource=self.resource,
            action=self.action,
            menu_uuid=self.menu_uuid,
        )


@dataclass(frozen=True, kw_only=True)
class CreatePermission(CreateMeta):
    org_uuid: str
    perm_code: str
    perm_name: str
    perm_type: int = PermType.API
    resource: str | None = None
    action: str | None = None
    menu_uuid: str | None = None

    def to_domain(self, uuid: str) -> Result[Permission, DomainError]:
        return Permission.create(
            self.org_uuid,
            uuid,
            self.perm_code,
            self.perm_name,
            perm_type=PermType(self.perm_type),
            resource=self.resource,
            action=self.action,
            menu_uuid=self.menu_uuid,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdatePermission(UpdateMeta):
    perm_name: str | None = None
    menu_uuid: str | None = None

    def apply_to(self, p: Permission) -> Result[Permission, DomainError]:
        return p.update(perm_name=self.perm_name, menu_uuid=self.menu_uuid).map(self.apply_meta)
