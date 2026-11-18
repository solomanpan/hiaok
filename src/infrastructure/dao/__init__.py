"""DAOs: table access + DO <-> entity conversion (``to_entity`` / ``to_do``)."""

from .base import BaseDao, EntityDao, LinkDao
from .organization import OrganizationDao, OrgDetailDao
from .role import MenuRoleDao, RoleDao, RolePermissionDao
from .simple import (
    DepartmentDao,
    EmployeeDao,
    MenuDao,
    PermissionDao,
    ProjectDao,
    SysConfigDao,
    SysLogDao,
    TenantDao,
    UserGroupDao,
)
from .user import UserDao, UserDetailDao, UserRoleDao

__all__ = [
    "BaseDao",
    "DepartmentDao",
    "EmployeeDao",
    "EntityDao",
    "LinkDao",
    "MenuDao",
    "MenuRoleDao",
    "OrgDetailDao",
    "OrganizationDao",
    "PermissionDao",
    "ProjectDao",
    "RoleDao",
    "RolePermissionDao",
    "SysConfigDao",
    "SysLogDao",
    "TenantDao",
    "UserDao",
    "UserDetailDao",
    "UserGroupDao",
    "UserRoleDao",
]
