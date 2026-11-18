from __future__ import annotations

from toolz import groupby

from ...domain.entity import Role
from ..dao import MenuRoleDao, RoleDao, RolePermissionDao
from ..database import RoutingDatabase
from ..do import RoleDO
from .base import SqlRepository


class SqlRoleRepository(SqlRepository[Role, RoleDO]):
    """``role`` + ``role_permission`` + ``menu_role``."""

    def __init__(self, db: RoutingDatabase) -> None:
        self._roles = RoleDao(db)
        super().__init__(db, self._roles)
        self._perms = RolePermissionDao(db)
        self._menus = MenuRoleDao(db)

    async def load_many(self, rows: list[RoleDO]) -> list[Role]:
        uuids = [r.role_uuid for r in rows]
        perms = groupby(lambda r: r.role_uuid, await self._perms.list_in(None, "role_uuid", uuids))
        menus = groupby(lambda r: r.role_uuid, await self._menus.list_in(None, "role_uuid", uuids))
        return [
            self._roles.to_entity(r, permissions=perms.get(r.role_uuid, []), menus=menus.get(r.role_uuid, []))
            for r in rows
        ]

    async def save_children(self, aggregate: Role) -> None:
        owner = ("role_uuid", aggregate.role_uuid)
        await self._perms.sync(
            aggregate.org_uuid, owner, ("permission_uuid",), {(p,) for p in aggregate.permission_uuids}
        )
        await self._menus.sync(aggregate.org_uuid, owner, ("menu_uuid",), {(m,) for m in aggregate.menu_uuids})

    async def delete_children(self, org_uuid: str, uuid: str) -> None:
        await self._perms.soft_delete(org_uuid, role_uuid=uuid)
        await self._menus.soft_delete(org_uuid, role_uuid=uuid)
