from __future__ import annotations

from datetime import date

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError, validation
from hiaok_core.facade import PasswordHasher
from hiaok_core.fp import AsyncResult, curry

from ...domain.entity import Employee
from ...domain.vo import PasswordHash, RawPassword, RoleAssignment
from ..model import DepartmentModel, EmployeeModel, OnboardEmployee, RegisterUser, UserModel
from ..service import DepartmentService, EmployeeService, OnboardingService, RoleService, TenantService
from ._checks import ensure_all_exist, ensure_exists


def _active(e: Employee) -> Result[Employee, DomainError]:
    if not e.enabled or e.leave_date is not None:
        return Error(validation("employee_inactive", f"employee '{e.employee_uuid}' is not active"))
    return Ok(e)


@curry
def appoint_department_head(
    departments: DepartmentService,
    employees: EmployeeService,
    org_uuid: str,
    department_uuid: str,
    employee_uuid: str | None,
):
    """``employee_uuid=None`` clears the head."""
    check = (
        AsyncResult.ok(None)
        if employee_uuid is None
        else AsyncResult.of(employees.get(org_uuid, employee_uuid)).bind(_active)
    )
    return check.bind(lambda _: departments.appoint_head(org_uuid, department_uuid, employee_uuid)).map(
        DepartmentModel.from_domain
    )


@curry
def transfer_employee(
    employees: EmployeeService, departments: DepartmentService, org_uuid: str, employee_uuid: str, department_uuid: str
):
    return (
        AsyncResult.of(departments.get(org_uuid, department_uuid))
        .bind(lambda _: employees.transfer(org_uuid, employee_uuid, department_uuid))
        .map(EmployeeModel.from_domain)
    )


@curry
def resign_employee(employees: EmployeeService, org_uuid: str, employee_uuid: str, leave_date: date):
    return AsyncResult.of(employees.resign(org_uuid, employee_uuid, leave_date)).map(EmployeeModel.from_domain)


@curry
def onboard_employee(
    onboarding: OnboardingService,
    departments: DepartmentService,
    tenants: TenantService,
    roles: RoleService,
    hasher: PasswordHasher,
    cmd: OnboardEmployee,
):
    """department exists -> (account? password policy, tenant, roles) -> hire + register + link in ONE tx."""
    org_uuid = cmd.employee.org_uuid

    async def account() -> Result[tuple[RegisterUser, PasswordHash, list[RoleAssignment]] | None, DomainError]:
        if cmd.username is None:
            return Ok(None)
        if cmd.tenant_uuid is None:
            return Error(validation("tenant_required", "tenant_uuid is required to open a login account"))
        tenant_uuid = cmd.tenant_uuid
        register = RegisterUser(
            org_uuid=org_uuid,
            tenant_uuid=tenant_uuid,
            username=cmd.username,
            password=cmd.password or "",
            email=cmd.employee.email,
            phone=cmd.employee.phone,
            nickname=cmd.employee.employee_name,
            role_uuids=cmd.role_uuids,
        )
        return await (
            AsyncResult.of(RawPassword.create(cmd.password))
            .ensure(lambda _: tenants.get(org_uuid, tenant_uuid))
            .ensure(lambda _: ensure_all_exist(roles, org_uuid, cmd.role_uuids))
            .map(
                lambda raw: (
                    register,
                    PasswordHash(hasher.hash(raw.value)),
                    [RoleAssignment(r) for r in cmd.role_uuids],
                )
            )
        )

    return (
        AsyncResult.of(ensure_exists(departments, org_uuid, cmd.employee.department_uuid))
        .bind(lambda _: account())
        .bind(lambda acc: onboarding.onboard(cmd.employee, acc))
        .map(
            lambda pair: (
                EmployeeModel.from_domain(pair[0]),
                None if pair[1] is None else UserModel.from_domain(pair[1]),
            )
        )
    )
