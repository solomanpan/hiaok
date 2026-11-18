from factories import ORG, MenuFactory, PermissionFactory, RoleFactory

from src.domain.enum import Status
from src.domain.service import authority


def test_factories_build_valid_event_free_entities():
    role = RoleFactory.build()
    assert role.org_uuid == ORG and role.enabled and role.events == ()
    assert role.permission_uuids == frozenset()
    a, b = RoleFactory.batch(2)
    assert a.role_uuid != b.role_uuid and a.role_code != b.role_code


def test_authority_with_factories():
    perms = [*PermissionFactory.batch(2), PermissionFactory.build(state=Status.DISABLED)]
    roles = [
        RoleFactory.build(permission_uuids=frozenset({perms[0].permission_uuid})),
        RoleFactory.build(permission_uuids=frozenset({perms[2].permission_uuid}), state=Status.DISABLED),
    ]
    assert authority.granted_permission_uuids(roles) == {perms[0].permission_uuid}
    assert authority.permission_codes(perms) == sorted(p.perm_code.value for p in perms[:2])
    assert authority.visible_menus([MenuFactory.build(), MenuFactory.build(visible=False)])[0].visible
