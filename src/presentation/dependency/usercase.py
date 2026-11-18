"""Usercases injected into endpoints: ``usercase: RegisterUserDep``.

Each provider partially applies a curried usercase with the services it needs.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date
from typing import Annotated

from expression import Result
from fastapi import Depends
from hiaok_core.exception import DomainError

from ...application.model import (
    AuthorityModel,
    CreateDepartment,
    CreateMenu,
    CreateOrganization,
    CreatePermission,
    CreateProject,
    CreateRole,
    CreateSysConfig,
    CreateTenant,
    CreateUserGroup,
    DepartmentModel,
    EmployeeModel,
    MenuModel,
    OnboardEmployee,
    OrganizationModel,
    OrgDetailModel,
    PermissionModel,
    ProjectModel,
    RegisterUser,
    RoleAssignmentModel,
    RoleModel,
    SysConfigModel,
    SysLogModel,
    TenantModel,
    TreeModel,
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
    UserGroupModel,
    UserModel,
)
from ...application.model.base import CreateCommand
from ...application.usercase import employee as employee_uc
from ...application.usercase import organization as org_uc
from ...application.usercase import role as role_uc
from ...application.usercase import sys_config as config_uc
from ...application.usercase import tree as tree_uc
from ...application.usercase import user as user_uc
from ...application.usercase.crud import CrudUserCases, crud_usercases
from ...domain.entity import Employee, User
from ...domain.repository import Page, PageQuery
from .resources import ResourcesDep
from .service import (
    DepartmentServiceDep,
    EmployeeServiceDep,
    MenuServiceDep,
    OnboardingServiceDep,
    OrganizationServiceDep,
    PermissionServiceDep,
    ProjectServiceDep,
    ProvisioningServiceDep,
    RoleServiceDep,
    SysConfigServiceDep,
    SysLogServiceDep,
    TenantServiceDep,
    UserGroupServiceDep,
    UserServiceDep,
)

type R[T] = Awaitable[Result[T, DomainError]]


# ---------------------------------------------------------------- CRUD (one bundle per aggregate)
type OrganizationCrud = CrudUserCases[OrganizationModel, CreateOrganization, UpdateOrganization]
type TenantCrud = CrudUserCases[TenantModel, CreateTenant, UpdateTenant]
type UserCrud = CrudUserCases[UserModel, CreateCommand[User], UpdateUser]  # create -> RegisterUserDep
type UserGroupCrud = CrudUserCases[UserGroupModel, CreateUserGroup, UpdateUserGroup]
type ProjectCrud = CrudUserCases[ProjectModel, CreateProject, UpdateProject]
type RoleCrud = CrudUserCases[RoleModel, CreateRole, UpdateRole]
type PermissionCrud = CrudUserCases[PermissionModel, CreatePermission, UpdatePermission]
type MenuCrud = CrudUserCases[MenuModel, CreateMenu, UpdateMenu]
type DepartmentCrud = CrudUserCases[DepartmentModel, CreateDepartment, UpdateDepartment]
type EmployeeCrud = CrudUserCases[
    EmployeeModel, CreateCommand[Employee], UpdateEmployee
]  # create -> OnboardEmployeeDep
type SysConfigCrud = CrudUserCases[SysConfigModel, CreateSysConfig, UpdateSysConfig]


def get_organization_crud(s: OrganizationServiceDep) -> OrganizationCrud:
    return crud_usercases(s, OrganizationModel.from_domain)


def get_tenant_crud(s: TenantServiceDep) -> TenantCrud:
    return crud_usercases(s, TenantModel.from_domain)


def get_user_crud(s: UserServiceDep) -> UserCrud:
    return crud_usercases(s, UserModel.from_domain)


def get_user_group_crud(s: UserGroupServiceDep) -> UserGroupCrud:
    return crud_usercases(s, UserGroupModel.from_domain)


def get_project_crud(s: ProjectServiceDep) -> ProjectCrud:
    return crud_usercases(s, ProjectModel.from_domain)


def get_role_crud(s: RoleServiceDep) -> RoleCrud:
    return crud_usercases(s, RoleModel.from_domain)


def get_permission_crud(s: PermissionServiceDep) -> PermissionCrud:
    return crud_usercases(s, PermissionModel.from_domain)


def get_menu_crud(s: MenuServiceDep) -> MenuCrud:
    return crud_usercases(s, MenuModel.from_domain)


def get_department_crud(s: DepartmentServiceDep) -> DepartmentCrud:
    return crud_usercases(s, DepartmentModel.from_domain)


def get_employee_crud(s: EmployeeServiceDep) -> EmployeeCrud:
    return crud_usercases(s, EmployeeModel.from_domain)


def get_sys_config_crud(s: SysConfigServiceDep) -> SysConfigCrud:
    return crud_usercases(s, SysConfigModel.from_domain)


OrganizationCrudDep = Annotated[OrganizationCrud, Depends(get_organization_crud)]
TenantCrudDep = Annotated[TenantCrud, Depends(get_tenant_crud)]
UserCrudDep = Annotated[UserCrud, Depends(get_user_crud)]
UserGroupCrudDep = Annotated[UserGroupCrud, Depends(get_user_group_crud)]
ProjectCrudDep = Annotated[ProjectCrud, Depends(get_project_crud)]
RoleCrudDep = Annotated[RoleCrud, Depends(get_role_crud)]
PermissionCrudDep = Annotated[PermissionCrud, Depends(get_permission_crud)]
MenuCrudDep = Annotated[MenuCrud, Depends(get_menu_crud)]
DepartmentCrudDep = Annotated[DepartmentCrud, Depends(get_department_crud)]
EmployeeCrudDep = Annotated[EmployeeCrud, Depends(get_employee_crud)]
SysConfigCrudDep = Annotated[SysConfigCrud, Depends(get_sys_config_crud)]


# ---------------------------------------------------------------- composite
type ProvisionOrganization = Callable[[CreateOrganization], R[OrganizationModel]]
type UpdateOrgDetail = Callable[[str, OrgDetailModel], R[OrganizationModel]]
type RegisterUserUC = Callable[[RegisterUser], R[UserModel]]
type AssignUserRoles = Callable[[str, str, list[RoleAssignmentModel]], R[UserModel]]
type ChangePassword = Callable[[str, str, str], R[None]]
type GetUserAuthorities = Callable[[str, str, str | None], R[AuthorityModel]]
type GrantRolePermissions = Callable[[str, str, list[str]], R[RoleModel]]
type AssignRoleMenus = Callable[[str, str, list[str]], R[RoleModel]]
type MenuTree = Callable[[str], Awaitable[list[TreeModel[MenuModel]]]]
type MoveMenu = Callable[[str, str, str | None], R[MenuModel]]
type DepartmentTree = Callable[[str], Awaitable[list[TreeModel[DepartmentModel]]]]
type MoveDepartment = Callable[[str, str, str | None], R[DepartmentModel]]
type GroupTree = Callable[[str], Awaitable[list[TreeModel[UserGroupModel]]]]
type MoveGroup = Callable[[str, str, str | None], R[UserGroupModel]]
type AppointDepartmentHead = Callable[[str, str, str | None], R[DepartmentModel]]
type OnboardEmployeeUC = Callable[[OnboardEmployee], R[tuple[EmployeeModel, UserModel | None]]]
type TransferEmployee = Callable[[str, str, str], R[EmployeeModel]]
type ResignEmployee = Callable[[str, str, date], R[EmployeeModel]]
type GetConfigByKey = Callable[[str, str], R[SysConfigModel]]
type ListLogs = Callable[[str, PageQuery, str | None], Awaitable[Page[SysLogModel]]]


def get_provision_organization(p: ProvisioningServiceDep) -> ProvisionOrganization:
    return org_uc.provision_organization(p)


def get_update_org_detail(s: OrganizationServiceDep) -> UpdateOrgDetail:
    return org_uc.update_org_detail(s)


def get_register_user(
    users: UserServiceDep, tenants: TenantServiceDep, roles: RoleServiceDep, r: ResourcesDep
) -> RegisterUserUC:
    return user_uc.register_user(users, tenants, roles, r.hasher)


def get_assign_user_roles(users: UserServiceDep, roles: RoleServiceDep) -> AssignUserRoles:
    return user_uc.assign_user_roles(users, roles)


def get_change_password(users: UserServiceDep, r: ResourcesDep) -> ChangePassword:
    return user_uc.change_password(users, r.hasher)


def get_user_authorities(
    users: UserServiceDep, roles: RoleServiceDep, perms: PermissionServiceDep, menus: MenuServiceDep
) -> GetUserAuthorities:
    return user_uc.get_user_authorities(users, roles, perms, menus)


def get_grant_role_permissions(roles: RoleServiceDep, perms: PermissionServiceDep) -> GrantRolePermissions:
    return role_uc.grant_role_permissions(roles, perms)


def get_assign_role_menus(roles: RoleServiceDep, menus: MenuServiceDep) -> AssignRoleMenus:
    return role_uc.assign_role_menus(roles, menus)


def get_menu_tree(menus: MenuServiceDep) -> MenuTree:
    return tree_uc.menu_tree(menus)


def get_move_menu(menus: MenuServiceDep) -> MoveMenu:
    return tree_uc.move_menu(menus)


def get_department_tree(depts: DepartmentServiceDep) -> DepartmentTree:
    return tree_uc.department_tree(depts)


def get_move_department(depts: DepartmentServiceDep) -> MoveDepartment:
    return tree_uc.move_department(depts)


def get_group_tree(groups: UserGroupServiceDep) -> GroupTree:
    return tree_uc.group_tree(groups)


def get_move_group(groups: UserGroupServiceDep) -> MoveGroup:
    return tree_uc.move_group(groups)


def get_appoint_department_head(depts: DepartmentServiceDep, emps: EmployeeServiceDep) -> AppointDepartmentHead:
    return employee_uc.appoint_department_head(depts, emps)


def get_onboard_employee(
    onboarding: OnboardingServiceDep,
    depts: DepartmentServiceDep,
    tenants: TenantServiceDep,
    roles: RoleServiceDep,
    r: ResourcesDep,
) -> OnboardEmployeeUC:
    return employee_uc.onboard_employee(onboarding, depts, tenants, roles, r.hasher)


def get_transfer_employee(emps: EmployeeServiceDep, depts: DepartmentServiceDep) -> TransferEmployee:
    return employee_uc.transfer_employee(emps, depts)


def get_resign_employee(emps: EmployeeServiceDep) -> ResignEmployee:
    return employee_uc.resign_employee(emps)


def get_config_by_key(configs: SysConfigServiceDep) -> GetConfigByKey:
    return config_uc.get_config_by_key(configs)


def get_list_logs(logs: SysLogServiceDep) -> ListLogs:
    return config_uc.list_logs(logs)


ProvisionOrganizationDep = Annotated[ProvisionOrganization, Depends(get_provision_organization)]
UpdateOrgDetailDep = Annotated[UpdateOrgDetail, Depends(get_update_org_detail)]
RegisterUserDep = Annotated[RegisterUserUC, Depends(get_register_user)]
AssignUserRolesDep = Annotated[AssignUserRoles, Depends(get_assign_user_roles)]
ChangePasswordDep = Annotated[ChangePassword, Depends(get_change_password)]
GetUserAuthoritiesDep = Annotated[GetUserAuthorities, Depends(get_user_authorities)]
GrantRolePermissionsDep = Annotated[GrantRolePermissions, Depends(get_grant_role_permissions)]
AssignRoleMenusDep = Annotated[AssignRoleMenus, Depends(get_assign_role_menus)]
MenuTreeDep = Annotated[MenuTree, Depends(get_menu_tree)]
MoveMenuDep = Annotated[MoveMenu, Depends(get_move_menu)]
DepartmentTreeDep = Annotated[DepartmentTree, Depends(get_department_tree)]
MoveDepartmentDep = Annotated[MoveDepartment, Depends(get_move_department)]
GroupTreeDep = Annotated[GroupTree, Depends(get_group_tree)]
MoveGroupDep = Annotated[MoveGroup, Depends(get_move_group)]
AppointDepartmentHeadDep = Annotated[AppointDepartmentHead, Depends(get_appoint_department_head)]
OnboardEmployeeDep = Annotated[OnboardEmployeeUC, Depends(get_onboard_employee)]
TransferEmployeeDep = Annotated[TransferEmployee, Depends(get_transfer_employee)]
ResignEmployeeDep = Annotated[ResignEmployee, Depends(get_resign_employee)]
GetConfigByKeyDep = Annotated[GetConfigByKey, Depends(get_config_by_key)]
ListLogsDep = Annotated[ListLogs, Depends(get_list_logs)]
