"""Self-referencing aggregates: tree read + cycle-safe move."""

from __future__ import annotations

from expression import Result
from hiaok_core.exception import DomainError
from hiaok_core.fp import AsyncResult

from ...domain.entity import Department, Menu, UserGroup
from ...domain.service.tree import TreeNode, build_tree, ensure_no_cycle
from .base import CrudService
from .datasource import master, slave


class MenuService(CrudService[Menu]):
    entity = "Menu"

    @slave
    async def tree(self, org_uuid: str) -> list[TreeNode[Menu]]:
        menus = await self._repo.list_all(org_uuid)
        return build_tree(menus, lambda m: m.menu_uuid, lambda m: m.parent_uuid, lambda m: m.sort_order)

    @master
    async def move(self, org_uuid: str, menu_uuid: str, parent_uuid: str | None) -> Result[Menu, DomainError]:
        menus = await self._repo.list_all(org_uuid)
        return await (
            AsyncResult.of(
                ensure_no_cycle(menus, lambda m: m.menu_uuid, lambda m: m.parent_uuid, menu_uuid, parent_uuid)
            )
            .bind(lambda _: self.load(org_uuid, menu_uuid))
            .bind(lambda m: m.move_to(parent_uuid))
            .bind(self.save)
        )


class DepartmentService(CrudService[Department]):
    entity = "Department"

    @slave
    async def tree(self, org_uuid: str) -> list[TreeNode[Department]]:
        depts = await self._repo.list_all(org_uuid)
        return build_tree(
            depts, lambda d: d.department_uuid, lambda d: d.parent_department_uuid, lambda d: d.sort_order
        )

    @master
    async def move(
        self, org_uuid: str, department_uuid: str, parent_uuid: str | None
    ) -> Result[Department, DomainError]:
        depts = await self._repo.list_all(org_uuid)
        return await (
            AsyncResult.of(
                ensure_no_cycle(
                    depts, lambda d: d.department_uuid, lambda d: d.parent_department_uuid, department_uuid, parent_uuid
                )
            )
            .bind(lambda _: self.load(org_uuid, department_uuid))
            .bind(lambda d: d.move_to(parent_uuid))
            .bind(self.save)
        )

    @master
    async def appoint_head(
        self, org_uuid: str, department_uuid: str, employee_uuid: str | None
    ) -> Result[Department, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, department_uuid))
            .map(lambda d: d.appoint_head(employee_uuid))
            .bind(self.save)
        )


class UserGroupService(CrudService[UserGroup]):
    entity = "UserGroup"

    @slave
    async def tree(self, org_uuid: str) -> list[TreeNode[UserGroup]]:
        groups = await self._repo.list_all(org_uuid)
        return build_tree(groups, lambda g: g.group_uuid, lambda g: g.parent_group_uuid, lambda g: g.sort_order)

    @master
    async def move(self, org_uuid: str, group_uuid: str, parent_uuid: str | None) -> Result[UserGroup, DomainError]:
        groups = await self._repo.list_all(org_uuid)
        return await (
            AsyncResult.of(
                ensure_no_cycle(groups, lambda g: g.group_uuid, lambda g: g.parent_group_uuid, group_uuid, parent_uuid)
            )
            .bind(lambda _: self.load(org_uuid, group_uuid))
            .bind(lambda g: g.move_to(parent_uuid))
            .bind(self.save)
        )
