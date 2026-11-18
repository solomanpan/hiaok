from __future__ import annotations

from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from typing import Any

from expression import Error, Ok, Result, effect
from hiaok_core.exception import DomainError, conflict

from ..enum import RoleType
from ..vo import Code, non_blank
from .base import AggregateRoot
from .event import RoleMenusChanged, RolePermissionsChanged


@dataclass(frozen=True, kw_only=True)
class Role(AggregateRoot):
    """``role`` + ``role_permission`` + ``menu_role`` (kept as uuid sets inside the aggregate)."""

    role_uuid: str
    tenant_uuid: str
    role_code: Code
    role_name: str
    role_type: RoleType = RoleType.CUSTOM
    permission_uuids: frozenset[str] = field(default_factory=frozenset)
    menu_uuids: frozenset[str] = field(default_factory=frozenset)

    @property
    def uuid(self) -> str:
        return self.role_uuid

    @staticmethod
    def create(
        org_uuid: str,
        role_uuid: str,
        tenant_uuid: str,
        role_code: str,
        role_name: str,
        *,
        role_type: RoleType = RoleType.CUSTOM,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Role, DomainError]:
        @effect.result[Role, DomainError]()
        def build() -> Generator[Any, Any, Role]:
            code = yield from Code.create(role_code, "role_code")
            name = yield from non_blank(role_name, "role_name")
            role = Role(
                org_uuid=org_uuid,
                role_uuid=role_uuid,
                tenant_uuid=tenant_uuid,
                role_code=code,
                role_name=name,
                role_type=RoleType(role_type),
                description=description,
                remark=remark,
            )
            return role.created()

        return build()

    def rename(self, role_name: str | None) -> Result[Role, DomainError]:
        if role_name is None:
            return Ok(self)
        return non_blank(role_name, "role_name").map(lambda name: self.changed(role_name=name))

    def grant_permissions(self, permission_uuids: Iterable[str]) -> Role:
        new = frozenset(permission_uuids)
        if new == self.permission_uuids:
            return self
        return self.changed(permission_uuids=new).record(
            RolePermissionsChanged(
                org_uuid=self.org_uuid, role_uuid=self.role_uuid, permission_uuids=tuple(sorted(new))
            )
        )

    def assign_menus(self, menu_uuids: Iterable[str]) -> Role:
        new = frozenset(menu_uuids)
        if new == self.menu_uuids:
            return self
        return self.changed(menu_uuids=new).record(
            RoleMenusChanged(org_uuid=self.org_uuid, role_uuid=self.role_uuid, menu_uuids=tuple(sorted(new)))
        )

    def ensure_deletable(self) -> Result[Role, DomainError]:
        if self.role_type is RoleType.SYSTEM:
            return Error(conflict("system_role", f"system role '{self.role_code}' cannot be deleted"))
        return Ok(self)
