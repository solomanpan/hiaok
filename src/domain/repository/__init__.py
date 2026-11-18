"""Repository interfaces (one per aggregate). Implementations: ``infrastructure/repository``."""

from typing import Protocol

from expression import Option

from ..entity import (
    Department,
    Employee,
    Menu,
    Organization,
    Permission,
    Project,
    Role,
    SysConfig,
    SysLog,
    Tenant,
    User,
    UserGroup,
)
from .base import Repository
from .page import Page, PageQuery


class OrganizationRepository(Repository[Organization], Protocol): ...


class TenantRepository(Repository[Tenant], Protocol): ...


class UserRepository(Repository[User], Protocol):
    async def find_by_username(self, org_uuid: str, tenant_uuid: str, username: str) -> Option[User]: ...


class UserGroupRepository(Repository[UserGroup], Protocol): ...


class ProjectRepository(Repository[Project], Protocol): ...


class RoleRepository(Repository[Role], Protocol): ...


class PermissionRepository(Repository[Permission], Protocol): ...


class MenuRepository(Repository[Menu], Protocol): ...


class DepartmentRepository(Repository[Department], Protocol): ...


class EmployeeRepository(Repository[Employee], Protocol): ...


class SysConfigRepository(Repository[SysConfig], Protocol):
    async def find_by_key(self, org_uuid: str, config_key: str) -> Option[SysConfig]: ...


class SysLogRepository(Protocol):
    """Append-only."""

    async def append(self, log: SysLog) -> None: ...

    async def get(self, org_uuid: str, log_uuid: str) -> Option[SysLog]: ...

    async def list(self, org_uuid: str, page: PageQuery, event_type: str | None = None) -> Page[SysLog]: ...


__all__ = [
    "DepartmentRepository",
    "EmployeeRepository",
    "MenuRepository",
    "OrganizationRepository",
    "Page",
    "PageQuery",
    "PermissionRepository",
    "ProjectRepository",
    "Repository",
    "RoleRepository",
    "SysConfigRepository",
    "SysLogRepository",
    "TenantRepository",
    "UserGroupRepository",
    "UserRepository",
]
