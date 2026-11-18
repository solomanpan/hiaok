from __future__ import annotations

from hiaok_core.fp import AsyncResult, curry

from ..model import RoleModel
from ..service import MenuService, PermissionService, RoleService
from ._checks import ensure_all_exist


@curry
def grant_role_permissions(
    roles: RoleService, permissions: PermissionService, org_uuid: str, role_uuid: str, permission_uuids: list[str]
):
    return (
        AsyncResult.of(ensure_all_exist(permissions, org_uuid, permission_uuids))
        .bind(lambda _: roles.grant_permissions(org_uuid, role_uuid, permission_uuids))
        .map(RoleModel.from_domain)
    )


@curry
def assign_role_menus(roles: RoleService, menus: MenuService, org_uuid: str, role_uuid: str, menu_uuids: list[str]):
    return (
        AsyncResult.of(ensure_all_exist(menus, org_uuid, menu_uuids))
        .bind(lambda _: roles.assign_menus(org_uuid, role_uuid, menu_uuids))
        .map(RoleModel.from_domain)
    )
