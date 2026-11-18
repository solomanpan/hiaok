from __future__ import annotations

from collections.abc import Iterable

from expression import Result
from hiaok_core.exception import DomainError
from hiaok_core.fp import AsyncResult

from ...domain.entity import Role
from .base import CrudService
from .datasource import master


class RoleService(CrudService[Role]):
    entity = "Role"

    @master
    async def grant_permissions(
        self, org_uuid: str, role_uuid: str, permission_uuids: Iterable[str]
    ) -> Result[Role, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, role_uuid))
            .map(lambda r: r.grant_permissions(permission_uuids))
            .bind(self.save)
        )

    @master
    async def assign_menus(self, org_uuid: str, role_uuid: str, menu_uuids: Iterable[str]) -> Result[Role, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, role_uuid)).map(lambda r: r.assign_menus(menu_uuids)).bind(self.save)
        )
