"""Data objects (DO): SQLAlchemy ORM rows, one class per table.

Importing this package registers every table on ``Base.metadata``.
"""

from .department import DepartmentDO
from .employee import EmployeeDO
from .menu import MenuDO
from .organization import OrganizationDO, OrgDetailDO
from .permission import PermissionDO
from .project import ProjectDO
from .role import MenuRoleDO, RoleDO, RolePermissionDO
from .sys_config import SysConfigDO
from .sys_log import SysLogDO
from .tenant import TenantDO
from .user import UserDetailDO, UserDO, UserRoleDO
from .user_group import UserGroupDO

__all__ = [
    "DepartmentDO",
    "EmployeeDO",
    "MenuDO",
    "MenuRoleDO",
    "OrgDetailDO",
    "OrganizationDO",
    "PermissionDO",
    "ProjectDO",
    "RoleDO",
    "RolePermissionDO",
    "SysConfigDO",
    "SysLogDO",
    "TenantDO",
    "UserDO",
    "UserDetailDO",
    "UserGroupDO",
    "UserRoleDO",
]
