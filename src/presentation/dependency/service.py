"""Application services: repositories (infrastructure) are wired into services here."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from ...application.service import (
    DepartmentService,
    EmployeeService,
    MenuService,
    OnboardingService,
    OrganizationService,
    PermissionService,
    ProjectService,
    ProvisioningService,
    RoleService,
    SysConfigService,
    SysLogService,
    TenantService,
    UserGroupService,
    UserService,
)
from ...infrastructure.repository import (
    SqlDepartmentRepository,
    SqlEmployeeRepository,
    SqlMenuRepository,
    SqlOrganizationRepository,
    SqlPermissionRepository,
    SqlProjectRepository,
    SqlRoleRepository,
    SqlSysConfigRepository,
    SqlSysLogRepository,
    SqlTenantRepository,
    SqlUserGroupRepository,
    SqlUserRepository,
)
from .resources import ResourcesDep


def get_organization_service(r: ResourcesDep) -> OrganizationService:
    return OrganizationService(r.tx, SqlOrganizationRepository(r.db), r.bus)


def get_tenant_service(r: ResourcesDep) -> TenantService:
    return TenantService(r.tx, SqlTenantRepository(r.db), r.bus)


def get_user_service(r: ResourcesDep) -> UserService:
    return UserService(r.tx, SqlUserRepository(r.db), r.bus)


def get_user_group_service(r: ResourcesDep) -> UserGroupService:
    return UserGroupService(r.tx, SqlUserGroupRepository(r.db), r.bus)


def get_project_service(r: ResourcesDep) -> ProjectService:
    return ProjectService(r.tx, SqlProjectRepository(r.db), r.bus)


def get_role_service(r: ResourcesDep) -> RoleService:
    return RoleService(r.tx, SqlRoleRepository(r.db), r.bus)


def get_permission_service(r: ResourcesDep) -> PermissionService:
    return PermissionService(r.tx, SqlPermissionRepository(r.db), r.bus)


def get_menu_service(r: ResourcesDep) -> MenuService:
    return MenuService(r.tx, SqlMenuRepository(r.db), r.bus)


def get_department_service(r: ResourcesDep) -> DepartmentService:
    return DepartmentService(r.tx, SqlDepartmentRepository(r.db), r.bus)


def get_employee_service(r: ResourcesDep) -> EmployeeService:
    return EmployeeService(r.tx, SqlEmployeeRepository(r.db), r.bus)


def get_sys_config_service(r: ResourcesDep) -> SysConfigService:
    return SysConfigService(r.tx, SqlSysConfigRepository(r.db), r.bus, r.cache, r.settings.redis.cache_ttl_seconds)


def get_sys_log_service(r: ResourcesDep) -> SysLogService:
    return SysLogService(r.tx, SqlSysLogRepository(r.db))


OrganizationServiceDep = Annotated[OrganizationService, Depends(get_organization_service)]
TenantServiceDep = Annotated[TenantService, Depends(get_tenant_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
UserGroupServiceDep = Annotated[UserGroupService, Depends(get_user_group_service)]
ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
RoleServiceDep = Annotated[RoleService, Depends(get_role_service)]
PermissionServiceDep = Annotated[PermissionService, Depends(get_permission_service)]
MenuServiceDep = Annotated[MenuService, Depends(get_menu_service)]
DepartmentServiceDep = Annotated[DepartmentService, Depends(get_department_service)]
EmployeeServiceDep = Annotated[EmployeeService, Depends(get_employee_service)]
SysConfigServiceDep = Annotated[SysConfigService, Depends(get_sys_config_service)]
SysLogServiceDep = Annotated[SysLogService, Depends(get_sys_log_service)]


def get_provisioning_service(
    r: ResourcesDep,
    orgs: OrganizationServiceDep,
    tenants: TenantServiceDep,
    roles: RoleServiceDep,
    configs: SysConfigServiceDep,
    permissions: PermissionServiceDep,
) -> ProvisioningService:
    return ProvisioningService(r.tx, r.bus, orgs, tenants, roles, configs, permissions)


def get_onboarding_service(r: ResourcesDep, employees: EmployeeServiceDep, users: UserServiceDep) -> OnboardingService:
    return OnboardingService(r.tx, r.bus, employees, users)


ProvisioningServiceDep = Annotated[ProvisioningService, Depends(get_provisioning_service)]
OnboardingServiceDep = Annotated[OnboardingService, Depends(get_onboarding_service)]
