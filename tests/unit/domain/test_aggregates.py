from support import err, of_type, ok

from src.domain.entity import Menu, Permission, Role
from src.domain.entity.event import EntityCreated, EntityUpdated, RoleMenusChanged, RolePermissionsChanged
from src.domain.enum import RoleType, Status

ORG, TENANT = "org-1", "tenant-1"


def _role(**kw) -> Role:
    role, _ = ok(Role.create(ORG, "r1", TENANT, "admin", "Admin", **kw)).pull_events()
    return role


# ---------------------------------------------------------------- Role
def test_role_create_records_entity_created():
    role = ok(Role.create(ORG, "r1", TENANT, "admin", "Admin"))
    assert [type(e) for e in role.events] == [EntityCreated]
    assert of_type(role.events[0], EntityCreated).entity_uuid == "r1"


def test_role_create_short_circuits_on_first_error():
    assert err(Role.create(ORG, "r1", TENANT, "bad code", "")).code == "invalid_role_code"
    assert err(Role.create(ORG, "r1", TENANT, "admin", " ")).code == "role_name_required"


def test_rename_records_changed_fields_and_is_noop_when_unchanged():
    role = _role()
    renamed = ok(role.rename("Root"))
    assert renamed.role_name == "Root"
    assert of_type(renamed.events[0], EntityUpdated).changed_fields == ("role_name",)
    assert ok(role.rename("Admin")).events == ()
    assert ok(role.rename(None)) is role


def test_grant_permissions_emits_business_event_once():
    role = _role().grant_permissions(["p2", "p1"])
    assert role.permission_uuids == {"p1", "p2"}
    assert [type(e) for e in role.events] == [EntityUpdated, RolePermissionsChanged]
    assert of_type(role.events[1], RolePermissionsChanged).permission_uuids == ("p1", "p2")
    assert role.grant_permissions(["p1", "p2"]) is role  # idempotent


def test_assign_menus():
    role = _role().assign_menus({"m1"})
    assert isinstance(role.events[-1], RoleMenusChanged)


def test_system_role_cannot_be_deleted():
    assert err(_role(role_type=RoleType.SYSTEM).ensure_deletable()).kind == "conflict"
    assert _role().ensure_deletable().is_ok()


def test_aggregates_are_immutable_and_compare_without_events():
    role = _role()
    changed = role.change_meta(state=Status.DISABLED)
    assert role.enabled and not changed.enabled
    assert role == role.record(*changed.events)  # events are excluded from equality


# ---------------------------------------------------------------- Permission / Menu
def test_permission_derives_resource_and_action():
    perm = ok(Permission.create(ORG, "p1", "project:create", "Create project"))
    assert (perm.resource, perm.action) == ("project", "create")
    wildcard = ok(Permission.create(ORG, "p2", "*", "All"))
    assert wildcard.action is None


def test_menu_cannot_be_its_own_parent():
    menu = ok(Menu.create(ORG, "m1", "home", "Home"))
    assert err(menu.move_to("m1")).code == "invalid_parent"
    assert ok(menu.move_to("m0")).parent_uuid == "m0"
