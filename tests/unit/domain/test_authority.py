import pytest
from support import ok

from src.domain.entity import Menu, Permission, Role
from src.domain.enum import Status
from src.domain.service import authority

ORG = "org-1"


def _role(uuid, perms=(), menus=(), state=Status.ENABLED):
    role = ok(Role.create(ORG, uuid, "t1", uuid, uuid)).grant_permissions(perms).assign_menus(menus)
    return role.change_meta(state=state)


def test_union_over_enabled_roles_only():
    roles = [_role("a", ["p1"], ["m1"]), _role("b", ["p2"]), _role("off", ["p3"], ["m3"], Status.DISABLED)]
    assert authority.granted_permission_uuids(roles) == {"p1", "p2"}
    assert authority.granted_menu_uuids(roles) == {"m1"}
    assert [r.role_uuid for r in authority.enabled_roles(roles)] == ["a", "b"]


def test_permission_codes_sorted_and_enabled_only():
    perms = [
        ok(Permission.create(ORG, "1", "user:read", "r")),
        ok(Permission.create(ORG, "2", "project:create", "c")),
        ok(Permission.create(ORG, "3", "x:y", "off")).change_meta(state=Status.DISABLED),
    ]
    assert authority.permission_codes(perms) == ["project:create", "user:read"]


def test_visible_menus():
    shown = ok(Menu.create(ORG, "m1", "home", "Home"))
    hidden = ok(Menu.create(ORG, "m2", "secret", "S", visible=False))
    assert authority.visible_menus([shown, hidden]) == [shown]


@pytest.mark.parametrize(
    ("codes", "required", "expected"),
    [
        (["project:create"], "project:create", True),
        (["project:*"], "project:delete", True),
        (["*"], "anything:at_all", True),
        (["project:read"], "project:create", False),
        (["user:*"], "project:create", False),
        ([], "project:create", False),
    ],
)
def test_is_granted(codes, required, expected):
    assert authority.is_granted(codes, required) is expected
