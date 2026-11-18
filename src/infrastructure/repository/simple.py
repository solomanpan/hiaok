"""Repositories for single-table aggregates: everything is generic, the DAO does the conversion."""

from __future__ import annotations

from expression import Option, Some, option

from ...domain.entity import Department, Employee, Menu, Permission, Project, SysConfig, SysLog, Tenant, UserGroup
from ...domain.repository import Page, PageQuery
from .. import dao
from ..database import RoutingDatabase
from ..do import (
    DepartmentDO,
    EmployeeDO,
    MenuDO,
    PermissionDO,
    ProjectDO,
    SysConfigDO,
    TenantDO,
    UserGroupDO,
)
from .base import SqlRepository


class SqlTenantRepository(SqlRepository[Tenant, TenantDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, dao.TenantDao(db))


class SqlUserGroupRepository(SqlRepository[UserGroup, UserGroupDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, dao.UserGroupDao(db))


class SqlProjectRepository(SqlRepository[Project, ProjectDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, dao.ProjectDao(db))


class SqlPermissionRepository(SqlRepository[Permission, PermissionDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, dao.PermissionDao(db))


class SqlMenuRepository(SqlRepository[Menu, MenuDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, dao.MenuDao(db))


class SqlDepartmentRepository(SqlRepository[Department, DepartmentDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, dao.DepartmentDao(db))


class SqlEmployeeRepository(SqlRepository[Employee, EmployeeDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, dao.EmployeeDao(db))


class SqlSysConfigRepository(SqlRepository[SysConfig, SysConfigDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        self._configs = dao.SysConfigDao(db)
        super().__init__(db, self._configs)

    async def find_by_key(self, org_uuid: str, config_key: str) -> Option[SysConfig]:
        row = await self._configs.find_one(org_uuid, config_key=config_key)
        return option.NOTHING if row is None else Some(self._configs.to_entity(row))


class SqlSysLogRepository:
    """Append-only; replays of the same event are ignored (ON CONFLICT DO NOTHING on log_uuid)."""

    def __init__(self, db: RoutingDatabase) -> None:
        self._logs = dao.SysLogDao(db)

    async def append(self, log: SysLog) -> None:
        await self._logs.insert_ignore(log)

    async def list(self, org_uuid: str, page: PageQuery, event_type: str | None = None) -> Page[SysLog]:
        filters = {} if event_type is None else {"event_type": event_type}
        rows, total = await self._logs.page(org_uuid, page.offset, page.limit, newest_first=True, **filters)
        return Page(tuple(self._logs.to_entity(r) for r in rows), total, page.offset, page.limit)
