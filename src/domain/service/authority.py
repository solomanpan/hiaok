"""Authorization rules: what a user may do = union over their enabled roles."""

from __future__ import annotations

from collections.abc import Iterable

from ..entity import Menu, Permission, Role


def enabled_roles(roles: Iterable[Role]) -> list[Role]:
    return [r for r in roles if r.enabled]


def granted_permission_uuids(roles: Iterable[Role]) -> frozenset[str]:
    return frozenset(uuid for r in roles if r.enabled for uuid in r.permission_uuids)


def granted_menu_uuids(roles: Iterable[Role]) -> frozenset[str]:
    return frozenset(uuid for r in roles if r.enabled for uuid in r.menu_uuids)


def permission_codes(permissions: Iterable[Permission]) -> list[str]:
    return sorted(p.perm_code.value for p in permissions if p.enabled)


def visible_menus(menus: Iterable[Menu]) -> list[Menu]:
    return [m for m in menus if m.enabled and m.visible]


def is_granted(codes: Iterable[str], required: str) -> bool:
    """``project:*`` grants every ``project:<action>``; ``*`` grants everything."""
    resource = required.partition(":")[0]
    return any(c in (required, "*", f"{resource}:*") for c in codes)
