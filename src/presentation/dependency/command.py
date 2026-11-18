"""Asynchronous writes: the submitter injected into endpoints, and the handler table the consumers run.

    endpoint  --WriteSubmitter-->  Kafka topic  --consumer-->  handlers[command_type]  -->  usecase  -->  DB

``build_write_handlers`` wires the same services / usecases the endpoints used to call directly, once, for the
consumer side (API nodes and ``hiaok worker``).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any

from fastapi import Depends

from ...application.model import (
    AppointHeadPayload,
    CreateDepartment,
    CreateMenu,
    CreateOrganization,
    CreatePermission,
    CreateProject,
    CreateRole,
    CreateSysConfig,
    CreateTenant,
    CreateUserGroup,
    MenusPayload,
    MovePayload,
    OrgDetailModel,
    PermissionsPayload,
    ResignPayload,
    RolesPayload,
    TransferPayload,
    UpdateDepartment,
    UpdateEmployee,
    UpdateMenu,
    UpdateOrganization,
    UpdatePermission,
    UpdateProject,
    UpdateRole,
    UpdateSysConfig,
    UpdateTenant,
    UpdateUser,
    UpdateUserGroup,
)
from ...application.usecase.command import CommandHandler, WriteSubmitter, typed, untyped
from ...infrastructure.resources import Resources
from .resources import ResourcesDep
from .service import (
    get_department_service,
    get_employee_service,
    get_menu_service,
    get_organization_service,
    get_permission_service,
    get_project_service,
    get_provisioning_service,
    get_role_service,
    get_sys_config_service,
    get_tenant_service,
    get_user_group_service,
    get_user_service,
)
from .usecase import (
    get_appoint_department_head,
    get_assign_role_menus,
    get_assign_user_roles,
    get_department_crud,
    get_employee_crud,
    get_grant_role_permissions,
    get_menu_crud,
    get_move_department,
    get_move_group,
    get_move_menu,
    get_organization_crud,
    get_permission_crud,
    get_project_crud,
    get_provision_organization,
    get_resign_employee,
    get_role_crud,
    get_sys_config_crud,
    get_tenant_crud,
    get_transfer_employee,
    get_update_org_detail,
    get_user_crud,
    get_user_group_crud,
)


def get_write_submitter(r: ResourcesDep) -> WriteSubmitter:
    return WriteSubmitter(r.bus)


WriteSubmitterDep = Annotated[WriteSubmitter, Depends(get_write_submitter)]


def _crud(entity: str, usecases: Any, create_model: type, update_model: type) -> dict[str, CommandHandler]:
    return {
        f"{entity}.create": typed(create_model, lambda c, m: usecases.create(m)),
        f"{entity}.update": typed(update_model, lambda c, m: usecases.update(c.org_uuid, c.target_uuid, m)),
        f"{entity}.delete": untyped(lambda c: usecases.delete(c.org_uuid, c.target_uuid)),
    }


def build_write_handlers(r: Resources) -> Mapping[str, CommandHandler]:
    """``command_type`` -> handler. Registered below: every asynchronous write the API accepts."""
    organizations, tenants, users, groups = (
        get_organization_service(r),
        get_tenant_service(r),
        get_user_service(r),
        get_user_group_service(r),
    )
    projects, roles, permissions, menus = (
        get_project_service(r),
        get_role_service(r),
        get_permission_service(r),
        get_menu_service(r),
    )
    departments, employees, configs = get_department_service(r), get_employee_service(r), get_sys_config_service(r)

    handlers: dict[str, CommandHandler] = {}
    handlers |= _crud("Tenant", get_tenant_crud(tenants), CreateTenant, UpdateTenant)
    handlers |= _crud("Project", get_project_crud(projects), CreateProject, UpdateProject)
    handlers |= _crud("Permission", get_permission_crud(permissions), CreatePermission, UpdatePermission)
    handlers |= _crud("UserGroup", get_user_group_crud(groups), CreateUserGroup, UpdateUserGroup)
    handlers |= _crud("Menu", get_menu_crud(menus), CreateMenu, UpdateMenu)
    handlers |= _crud("Department", get_department_crud(departments), CreateDepartment, UpdateDepartment)
    handlers |= _crud("Role", get_role_crud(roles), CreateRole, UpdateRole)
    handlers |= _crud("SysConfig", get_sys_config_crud(configs), CreateSysConfig, UpdateSysConfig)

    # organization: the uuid is the organization itself
    org_crud = get_organization_crud(organizations)
    provision = get_provision_organization(get_provisioning_service(r, organizations, tenants, roles, configs))
    update_detail = get_update_org_detail(organizations)
    handlers["Organization.create"] = typed(CreateOrganization, lambda c, m: provision(m))
    handlers["Organization.update"] = typed(UpdateOrganization, lambda c, m: org_crud.update(c.org_uuid, c.org_uuid, m))
    handlers["Organization.update_detail"] = typed(OrgDetailModel, lambda c, m: update_detail(c.org_uuid, m))
    handlers["Organization.delete"] = untyped(lambda c: org_crud.delete(c.org_uuid, c.org_uuid))

    # user: registration and password change stay synchronous (they carry a clear-text password)
    user_crud = get_user_crud(users)
    assign_roles = get_assign_user_roles(users, roles)
    handlers["User.update"] = typed(UpdateUser, lambda c, m: user_crud.update(c.org_uuid, c.target_uuid, m))
    handlers["User.delete"] = untyped(lambda c: user_crud.delete(c.org_uuid, c.target_uuid))
    handlers["User.assign_roles"] = typed(
        RolesPayload, lambda c, m: assign_roles(c.org_uuid, c.target_uuid, list(m.roles))
    )

    # employee: onboarding (optional account + password) stays synchronous
    employee_crud = get_employee_crud(employees)
    transfer = get_transfer_employee(employees, departments)
    resign = get_resign_employee(employees)
    handlers["Employee.update"] = typed(UpdateEmployee, lambda c, m: employee_crud.update(c.org_uuid, c.target_uuid, m))
    handlers["Employee.delete"] = untyped(lambda c: employee_crud.delete(c.org_uuid, c.target_uuid))
    handlers["Employee.transfer"] = typed(
        TransferPayload, lambda c, m: transfer(c.org_uuid, c.target_uuid, m.department_uuid)
    )
    handlers["Employee.resign"] = typed(ResignPayload, lambda c, m: resign(c.org_uuid, c.target_uuid, m.leave_date))

    # trees
    move_menu, move_department, move_group = (
        get_move_menu(menus),
        get_move_department(departments),
        get_move_group(groups),
    )
    handlers["Menu.move"] = typed(MovePayload, lambda c, m: move_menu(c.org_uuid, c.target_uuid, m.parent_uuid))
    handlers["Department.move"] = typed(
        MovePayload, lambda c, m: move_department(c.org_uuid, c.target_uuid, m.parent_uuid)
    )
    handlers["UserGroup.move"] = typed(MovePayload, lambda c, m: move_group(c.org_uuid, c.target_uuid, m.parent_uuid))
    appoint = get_appoint_department_head(departments, employees)
    handlers["Department.appoint_head"] = typed(
        AppointHeadPayload, lambda c, m: appoint(c.org_uuid, c.target_uuid, m.employee_uuid)
    )

    # role
    grant = get_grant_role_permissions(roles, permissions)
    assign_menus = get_assign_role_menus(roles, menus)
    handlers["Role.grant_permissions"] = typed(
        PermissionsPayload, lambda c, m: grant(c.org_uuid, c.target_uuid, list(m.permission_uuids))
    )
    handlers["Role.assign_menus"] = typed(
        MenusPayload, lambda c, m: assign_menus(c.org_uuid, c.target_uuid, list(m.menu_uuids))
    )
    return handlers
