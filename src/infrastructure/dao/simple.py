"""DAOs for single-table entities: queries + ``to_entity`` / ``to_do``."""

from __future__ import annotations

from hiaok_core.context import current_context
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert

from ...domain.entity import Department, Employee, Menu, Permission, Project, SysConfig, SysLog, Tenant, UserGroup
from ...domain.enum import ConfigValueType, LogType, MenuType, PermType
from ...domain.vo import Code, Email, PhoneNumber, text_or_none
from ..database import ALIVE, RoutingDatabase
from ..do import (
    DepartmentDO,
    EmployeeDO,
    MenuDO,
    PermissionDO,
    ProjectDO,
    SysConfigDO,
    SysLogDO,
    TenantDO,
    UserGroupDO,
)
from .base import EntityDao, entity_kwargs


class TenantDao(EntityDao[TenantDO, Tenant]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, TenantDO, "tenant_uuid")

    def to_entity(self, do: TenantDO) -> Tenant:
        return Tenant(
            **entity_kwargs(do),
            tenant_uuid=do.tenant_uuid,
            tenant_code=Code(do.tenant_code),
            tenant_name=do.tenant_name,
            expire_time=do.expire_time,
        )

    def to_do(self, entity: Tenant, do: TenantDO | None = None) -> TenantDO:
        target = self.new_or(do, entity)
        target.tenant_uuid = entity.tenant_uuid
        target.tenant_code = entity.tenant_code.value
        target.tenant_name = entity.tenant_name
        target.expire_time = entity.expire_time
        return target


class UserGroupDao(EntityDao[UserGroupDO, UserGroup]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, UserGroupDO, "group_uuid")

    def to_entity(self, do: UserGroupDO) -> UserGroup:
        return UserGroup(
            **entity_kwargs(do),
            group_uuid=do.group_uuid,
            tenant_uuid=do.tenant_uuid,
            group_code=Code(do.group_code),
            group_name=do.group_name,
            parent_group_uuid=do.parent_group_uuid,
            sort_order=do.sort_order,
        )

    def to_do(self, entity: UserGroup, do: UserGroupDO | None = None) -> UserGroupDO:
        target = self.new_or(do, entity)
        target.group_uuid = entity.group_uuid
        target.tenant_uuid = entity.tenant_uuid
        target.group_code = entity.group_code.value
        target.group_name = entity.group_name
        target.parent_group_uuid = entity.parent_group_uuid
        target.sort_order = entity.sort_order
        return target


class ProjectDao(EntityDao[ProjectDO, Project]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, ProjectDO, "project_uuid")

    def to_entity(self, do: ProjectDO) -> Project:
        return Project(
            **entity_kwargs(do),
            project_uuid=do.project_uuid,
            tenant_uuid=do.tenant_uuid,
            project_code=Code(do.project_code),
            project_name=do.project_name,
            owner_user_uuid=do.owner_user_uuid,
        )

    def to_do(self, entity: Project, do: ProjectDO | None = None) -> ProjectDO:
        target = self.new_or(do, entity)
        target.project_uuid = entity.project_uuid
        target.tenant_uuid = entity.tenant_uuid
        target.project_code = entity.project_code.value
        target.project_name = entity.project_name
        target.owner_user_uuid = entity.owner_user_uuid
        return target


class PermissionDao(EntityDao[PermissionDO, Permission]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, PermissionDO, "permission_uuid")

    def to_entity(self, do: PermissionDO) -> Permission:
        return Permission(
            **entity_kwargs(do),
            permission_uuid=do.permission_uuid,
            perm_code=Code(do.perm_code),
            perm_name=do.perm_name,
            perm_type=PermType(do.perm_type),
            resource=do.resource,
            action=do.action,
            menu_uuid=do.menu_uuid,
        )

    def to_do(self, entity: Permission, do: PermissionDO | None = None) -> PermissionDO:
        target = self.new_or(do, entity)
        target.permission_uuid = entity.permission_uuid
        target.perm_code = entity.perm_code.value
        target.perm_name = entity.perm_name
        target.perm_type = int(entity.perm_type)
        target.resource = entity.resource
        target.action = entity.action
        target.menu_uuid = entity.menu_uuid
        return target


class MenuDao(EntityDao[MenuDO, Menu]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, MenuDO, "menu_uuid")

    def to_entity(self, do: MenuDO) -> Menu:
        return Menu(
            **entity_kwargs(do),
            menu_uuid=do.menu_uuid,
            menu_code=Code(do.menu_code),
            menu_name=do.menu_name,
            menu_type=MenuType(do.menu_type),
            parent_uuid=do.parent_uuid,
            path=do.path,
            component=do.component,
            icon=do.icon,
            sort_order=do.sort_order,
            visible=do.visible,
        )

    def to_do(self, entity: Menu, do: MenuDO | None = None) -> MenuDO:
        target = self.new_or(do, entity)
        target.menu_uuid = entity.menu_uuid
        target.menu_code = entity.menu_code.value
        target.menu_name = entity.menu_name
        target.menu_type = int(entity.menu_type)
        target.parent_uuid = entity.parent_uuid
        target.path = entity.path
        target.component = entity.component
        target.icon = entity.icon
        target.sort_order = entity.sort_order
        target.visible = entity.visible
        return target


class DepartmentDao(EntityDao[DepartmentDO, Department]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, DepartmentDO, "department_uuid")

    def to_entity(self, do: DepartmentDO) -> Department:
        return Department(
            **entity_kwargs(do),
            department_uuid=do.department_uuid,
            department_code=Code(do.department_code),
            department_name=do.department_name,
            parent_department_uuid=do.parent_department_uuid,
            employee_uuid=do.employee_uuid,
            sort_order=do.sort_order,
        )

    def to_do(self, entity: Department, do: DepartmentDO | None = None) -> DepartmentDO:
        target = self.new_or(do, entity)
        target.department_uuid = entity.department_uuid
        target.department_code = entity.department_code.value
        target.department_name = entity.department_name
        target.parent_department_uuid = entity.parent_department_uuid
        target.employee_uuid = entity.employee_uuid
        target.sort_order = entity.sort_order
        return target


class EmployeeDao(EntityDao[EmployeeDO, Employee]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, EmployeeDO, "employee_uuid")

    def to_entity(self, do: EmployeeDO) -> Employee:
        return Employee(
            **entity_kwargs(do),
            employee_uuid=do.employee_uuid,
            employee_no=Code(do.employee_no),
            employee_name=do.employee_name,
            department_uuid=do.department_uuid,
            user_uuid=do.user_uuid,
            email=Email(do.email) if do.email else None,
            phone=PhoneNumber(do.phone) if do.phone else None,
            position=do.position,
            hire_date=do.hire_date,
            leave_date=do.leave_date,
        )

    def to_do(self, entity: Employee, do: EmployeeDO | None = None) -> EmployeeDO:
        target = self.new_or(do, entity)
        target.employee_uuid = entity.employee_uuid
        target.employee_no = entity.employee_no.value
        target.employee_name = entity.employee_name
        target.department_uuid = entity.department_uuid
        target.user_uuid = entity.user_uuid
        target.email = text_or_none(entity.email)
        target.phone = text_or_none(entity.phone)
        target.position = entity.position
        target.hire_date = entity.hire_date
        target.leave_date = entity.leave_date
        return target


class SysConfigDao(EntityDao[SysConfigDO, SysConfig]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, SysConfigDO, "config_uuid")

    def to_entity(self, do: SysConfigDO) -> SysConfig:
        return SysConfig(
            **entity_kwargs(do),
            config_uuid=do.config_uuid,
            config_key=Code(do.config_key),
            config_value=do.config_value,
            value_type=ConfigValueType(do.value_type),
            config_group=do.config_group,
        )

    def to_do(self, entity: SysConfig, do: SysConfigDO | None = None) -> SysConfigDO:
        target = self.new_or(do, entity)
        target.config_uuid = entity.config_uuid
        target.config_key = entity.config_key.value
        target.config_value = entity.config_value
        target.value_type = entity.value_type.value
        target.config_group = entity.config_group
        return target


class SysLogDao(EntityDao[SysLogDO, SysLog]):
    # columns written on append (id / audit / delete_flag are filled by the database)
    INSERT_COLUMNS = (
        "org_uuid",
        "log_uuid",
        "log_type",
        "event_type",
        "aggregate_id",
        "trace_id",
        "content",
        "occurred_at",
        "description",
        "remark",
        "state",
    )

    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, SysLogDO, "log_uuid")

    def to_entity(self, do: SysLogDO) -> SysLog:
        return SysLog(
            **entity_kwargs(do),
            log_uuid=do.log_uuid,
            log_type=LogType(do.log_type),
            event_type=do.event_type,
            aggregate_id=do.aggregate_id,
            trace_id=do.trace_id,
            content=do.content,
            occurred_at=do.occurred_at,
        )

    def to_do(self, entity: SysLog, do: SysLogDO | None = None) -> SysLogDO:
        target = self.new_or(do, entity)
        target.log_uuid = entity.log_uuid
        target.log_type = entity.log_type.value
        target.event_type = entity.event_type
        target.aggregate_id = entity.aggregate_id
        target.trace_id = entity.trace_id
        target.content = entity.content
        target.occurred_at = entity.occurred_at
        return target

    async def insert_ignore(self, log: SysLog) -> None:
        """Idempotent append: a replayed event (same log_uuid) is silently skipped."""
        row = self.to_do(log)
        values = {c: getattr(row, c) for c in self.INSERT_COLUMNS}
        stmt = (
            insert(SysLogDO)
            .values(**values, opr=current_context().operator)
            .on_conflict_do_nothing(index_elements=["log_uuid"], index_where=text(ALIVE))
        )
        await self.session.execute(stmt)
