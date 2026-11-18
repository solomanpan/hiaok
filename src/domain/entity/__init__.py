"""Entities. An aggregate root is just the entity that owns a consistency boundary.

Domain events live in ``src.domain.entity.event`` (importing it registers every event type).
"""

from .base import AggregateRoot, Entity
from .department import Department
from .employee import Employee
from .menu import Menu
from .org_detail import OrgDetail
from .organization import Organization
from .permission import Permission
from .project import Project
from .role import Role
from .sys_config import SysConfig
from .sys_log import SysLog
from .tenant import Tenant
from .user import User
from .user_detail import UserDetail
from .user_group import UserGroup

__all__ = [
    "AggregateRoot",
    "Department",
    "Employee",
    "Entity",
    "Menu",
    "OrgDetail",
    "Organization",
    "Permission",
    "Project",
    "Role",
    "SysConfig",
    "SysLog",
    "Tenant",
    "User",
    "UserDetail",
    "UserGroup",
]
