"""``role`` (root) + ``role_permission`` / ``menu_role`` (link tables)."""

from __future__ import annotations

from collections.abc import Iterable

from ...domain.entity import Role
from ...domain.enum import RoleType
from ...domain.vo import Code
from ..database import RoutingDatabase
from ..do import MenuRoleDO, RoleDO, RolePermissionDO
from .base import EntityDao, LinkDao, entity_kwargs


class RoleDao(EntityDao[RoleDO, Role]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, RoleDO, "role_uuid")

    def to_entity(
        self,
        do: RoleDO,
        *,
        permissions: Iterable[RolePermissionDO] = (),
        menus: Iterable[MenuRoleDO] = (),
    ) -> Role:
        return Role(
            **entity_kwargs(do),
            role_uuid=do.role_uuid,
            tenant_uuid=do.tenant_uuid,
            role_code=Code(do.role_code),
            role_name=do.role_name,
            role_type=RoleType(do.role_type),
            permission_uuids=frozenset(p.permission_uuid for p in permissions),
            menu_uuids=frozenset(m.menu_uuid for m in menus),
        )

    def to_do(self, entity: Role, do: RoleDO | None = None) -> RoleDO:
        """Root row only; the link rows are synced by ``RolePermissionDao`` / ``MenuRoleDao``."""
        target = self.new_or(do, entity)
        target.role_uuid = entity.role_uuid
        target.tenant_uuid = entity.tenant_uuid
        target.role_code = entity.role_code.value
        target.role_name = entity.role_name
        target.role_type = int(entity.role_type)
        return target


class RolePermissionDao(LinkDao[RolePermissionDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, RolePermissionDO, "role_uuid")


class MenuRoleDao(LinkDao[MenuRoleDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, MenuRoleDO, "role_uuid")
