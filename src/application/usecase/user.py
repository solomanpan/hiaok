from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError, validation
from hiaok_core.facade import PasswordHasher
from hiaok_core.fp import AsyncResult, curry

from ...domain.entity import Role, User
from ...domain.service import authority
from ...domain.service.tree import build_tree
from ...domain.vo import PasswordHash, RawPassword, RoleAssignment
from ..model import (
    AuthorityModel,
    MenuModel,
    RegisterUser,
    RoleAssignmentModel,
    TreeModel,
    UserModel,
)
from ..service import MenuService, PermissionService, RoleService, TenantService, UserService
from ._checks import ensure_all_exist


def _same_tenant(roles: Iterable[Role], tenant_uuid: str) -> Result[list[Role], DomainError]:
    roles = list(roles)
    foreign = sorted(r.role_code.value for r in roles if r.tenant_uuid != tenant_uuid)
    if foreign:
        return Error(validation("role_tenant_mismatch", f"roles {foreign} belong to another tenant"))
    return Ok(roles)


@curry
def register_user(
    users: UserService, tenants: TenantService, roles: RoleService, hasher: PasswordHasher, cmd: RegisterUser
):
    """password policy -> tenant active -> roles exist in that tenant -> hash -> save (one @master tx)."""
    assignments = [RoleAssignment(r) for r in cmd.role_uuids]
    return (
        AsyncResult.of(RawPassword.create(cmd.password))
        .ensure(
            lambda _: AsyncResult.of(tenants.get(cmd.org_uuid, cmd.tenant_uuid)).bind(
                lambda t: t.ensure_active(datetime.now(UTC))
            )
        )
        .ensure(
            lambda _: AsyncResult.of(ensure_all_exist(roles, cmd.org_uuid, cmd.role_uuids)).bind(
                lambda found: _same_tenant(found, cmd.tenant_uuid)
            )
        )
        .map(lambda raw: PasswordHash(hasher.hash(raw.value)))
        .bind(lambda pw: users.register(cmd, pw, assignments))
        .map(UserModel.from_domain)
    )


@curry
def assign_user_roles(
    users: UserService, roles: RoleService, org_uuid: str, user_uuid: str, assignments: list[RoleAssignmentModel]
):
    wanted = [a.to_domain() for a in assignments]
    return (
        AsyncResult.of(users.get(org_uuid, user_uuid))
        .ensure(
            lambda user: AsyncResult.of(ensure_all_exist(roles, org_uuid, {a.role_uuid for a in wanted})).bind(
                lambda found: _same_tenant(found, user.tenant_uuid)
            )
        )
        .bind(lambda _: users.assign_roles(org_uuid, user_uuid, wanted))
        .map(UserModel.from_domain)
    )


@curry
def change_password(users: UserService, hasher: PasswordHasher, org_uuid: str, user_uuid: str, new_password: str):
    return (
        AsyncResult.of(RawPassword.create(new_password))
        .map(lambda raw: PasswordHash(hasher.hash(raw.value)))
        .bind(lambda pw: users.change_password(org_uuid, user_uuid, pw))
        .map(lambda _: None)
    )


@curry
def get_user_authorities(
    users: UserService,
    roles: RoleService,
    permissions: PermissionService,
    menus: MenuService,
    org_uuid: str,
    user_uuid: str,
    project_uuid: str | None = None,
):
    """user -> enabled roles -> union(permissions) + union(menus) -> codes + menu tree."""

    async def resolve(user: User) -> AuthorityModel:
        granted = authority.enabled_roles(await roles.list_by_uuids(org_uuid, user.role_uuids(project_uuid)))
        perms = await permissions.list_by_uuids(org_uuid, authority.granted_permission_uuids(granted))
        visible = authority.visible_menus(await menus.list_by_uuids(org_uuid, authority.granted_menu_uuids(granted)))
        tree = build_tree(visible, lambda m: m.menu_uuid, lambda m: m.parent_uuid, lambda m: m.sort_order)
        return AuthorityModel(
            user_uuid=user.user_uuid,
            role_codes=sorted(r.role_code.value for r in granted),
            permission_codes=authority.permission_codes(perms),
            menus=TreeModel.from_nodes(tree, MenuModel.from_domain),
        )

    return AsyncResult.of(users.get(org_uuid, user_uuid)).ensure(_enabled).map(resolve)


def _enabled(user: User) -> Result[User, DomainError]:
    return Ok(user) if user.enabled else Error(validation("user_disabled", f"user '{user.user_uuid}' is disabled"))
