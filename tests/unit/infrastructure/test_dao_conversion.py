"""DO <-> entity conversion lives in the DAOs; it needs no database (DOs are plain mapped objects)."""

from typing import cast

from support import ok

from src.domain.entity import Employee, Organization, Role, SysLog, User
from src.domain.enum import LogType, Status
from src.domain.vo import PasswordHash, RoleAssignment
from src.infrastructure.dao import EmployeeDao, OrganizationDao, RoleDao, SysLogDao, UserDao
from src.infrastructure.database import RoutingDatabase
from src.infrastructure.do import MenuRoleDO, RolePermissionDO, UserRoleDO

DB = cast(RoutingDatabase, None)  # conversions never touch the session
ORG = "org-1"


def test_single_table_round_trip():
    dao = EmployeeDao(DB)
    emp = ok(Employee.hire(ORG, "e1", "E-001", "Taro", email="taro@example.com")).change_meta(remark="r")
    emp, _ = emp.pull_events()

    row = dao.to_do(emp)
    assert (row.employee_uuid, row.employee_no, row.email, row.remark) == ("e1", "E-001", "taro@example.com", "r")
    assert dao.to_entity(row) == emp


def test_to_do_fills_the_loaded_row_in_place():
    dao = EmployeeDao(DB)
    emp, _ = ok(Employee.hire(ORG, "e1", "E-001", "Taro")).pull_events()
    existing = dao.to_do(emp)
    existing.id = 42

    renamed = ok(emp.update(employee_name="Jiro"))
    same = dao.to_do(renamed, existing)

    assert same is existing and same.id == 42 and same.employee_name == "Jiro"


def test_root_dao_takes_child_rows_as_keyword_arguments():
    dao = RoleDao(DB)
    role, _ = ok(Role.create(ORG, "r1", "t1", "admin", "Admin")).pull_events()
    row = dao.to_do(role)

    perms = [RolePermissionDO(org_uuid=ORG, role_uuid="r1", permission_uuid=p) for p in ("p1", "p2")]
    menus = [MenuRoleDO(org_uuid=ORG, role_uuid="r1", menu_uuid="m1")]
    loaded = dao.to_entity(row, permissions=perms, menus=menus)

    assert loaded.permission_uuids == {"p1", "p2"} and loaded.menu_uuids == {"m1"}
    assert dao.to_entity(row).permission_uuids == frozenset()


def test_user_with_detail_and_roles():
    dao = UserDao(DB)
    registered = ok(User.register(ORG, "u1", "t1", "taro", PasswordHash("hash")))
    user, _ = ok(registered.assign_roles([RoleAssignment("r1")])).pull_events()
    row = dao.to_do(user)
    loaded = dao.to_entity(row, roles=[UserRoleDO(org_uuid=ORG, user_uuid="u1", role_uuid="r1", project_uuid="")])

    assert loaded.username == user.username and loaded.roles == {RoleAssignment("r1")}
    assert loaded.detail.user_uuid == "u1"  # missing detail row -> empty detail


def test_organization_without_detail_row():
    dao = OrganizationDao(DB)
    org, _ = ok(Organization.create(ORG, "acme", "ACME")).pull_events()
    loaded = dao.to_entity(dao.to_do(org))
    assert loaded.org_code == org.org_code and loaded.detail.org_uuid == ORG


def test_sys_log():
    dao = SysLogDao(DB)
    log = SysLog(org_uuid=ORG, log_uuid="l1", log_type=LogType.EVENT, event_type="X", aggregate_id="a1")
    row = dao.to_do(log)
    assert row.log_type == "event" and row.state == Status.ENABLED
    assert dao.to_entity(row).log_uuid == "l1"
