"""Tree reads + moves for menu / department / user_group."""

from __future__ import annotations

from hiaok_core.fp import AsyncResult, curry

from ..model import DepartmentModel, MenuModel, TreeModel, UserGroupModel
from ..service import DepartmentService, MenuService, UserGroupService


@curry
async def menu_tree(menus: MenuService, org_uuid: str) -> list[TreeModel[MenuModel]]:
    return TreeModel.from_nodes(await menus.tree(org_uuid), MenuModel.from_domain)


@curry
def move_menu(menus: MenuService, org_uuid: str, menu_uuid: str, parent_uuid: str | None):
    return AsyncResult.of(menus.move(org_uuid, menu_uuid, parent_uuid)).map(MenuModel.from_domain)


@curry
async def department_tree(departments: DepartmentService, org_uuid: str) -> list[TreeModel[DepartmentModel]]:
    return TreeModel.from_nodes(await departments.tree(org_uuid), DepartmentModel.from_domain)


@curry
def move_department(departments: DepartmentService, org_uuid: str, department_uuid: str, parent_uuid: str | None):
    return AsyncResult.of(departments.move(org_uuid, department_uuid, parent_uuid)).map(DepartmentModel.from_domain)


@curry
async def group_tree(groups: UserGroupService, org_uuid: str) -> list[TreeModel[UserGroupModel]]:
    return TreeModel.from_nodes(await groups.tree(org_uuid), UserGroupModel.from_domain)


@curry
def move_group(groups: UserGroupService, org_uuid: str, group_uuid: str, parent_uuid: str | None):
    return AsyncResult.of(groups.move(org_uuid, group_uuid, parent_uuid)).map(UserGroupModel.from_domain)
