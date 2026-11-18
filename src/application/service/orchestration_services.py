"""Atomic multi-aggregate writes.

The outer ``@master`` opens ONE transaction; the inner services' ``@master`` methods join it, so either every
aggregate is persisted or none is. Events from all of them are published after that single commit.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError
from hiaok_core.facade import EventPublisher, IdGenerator, TransactionManager, uuid_hex
from hiaok_core.fp import AsyncResult

from ...domain.entity import Employee, Organization, Role, Tenant, User
from ...domain.entity.event import OrganizationProvisioned
from ...domain.enum import RoleType
from ...domain.vo import PasswordHash, RoleAssignment
from ..model import (
    CreateEmployee,
    CreateOrganization,
    CreateRole,
    CreateSysConfig,
    CreateTenant,
    RegisterUser,
)
from .base import ApplicationService
from .datasource import master
from .employee_service import EmployeeService
from .organization_service import OrganizationService
from .role_service import RoleService
from .simple_services import TenantService
from .sys_config_service import SysConfigService
from .user_service import UserService

DEFAULT_CONFIGS: tuple[tuple[str, str, str], ...] = (
    ("security.password.min_length", "8", "int"),
    ("security.session.ttl_minutes", "120", "int"),
    ("ui.default_locale", "ja-JP", "string"),
)


@dataclass(frozen=True)
class Provisioned:
    organization: Organization
    tenant: Tenant
    admin_role: Role


class ProvisioningService(ApplicationService):
    def __init__(
        self,
        tx: TransactionManager,
        publisher: EventPublisher,
        organizations: OrganizationService,
        tenants: TenantService,
        roles: RoleService,
        configs: SysConfigService,
        new_id: IdGenerator = uuid_hex,
    ) -> None:
        super().__init__(tx, publisher, new_id)
        self._orgs, self._tenants, self._roles, self._configs = organizations, tenants, roles, configs

    @master
    async def provision(self, cmd: CreateOrganization) -> Result[Provisioned, DomainError]:
        """organization + org_detail + default tenant + ORG_ADMIN system role + default sys_config."""
        return await (
            AsyncResult.of(self._orgs.create(cmd))
            .bind(self._with_default_tenant)
            .bind(self._with_admin_role)
            .ensure(lambda p: self._seed_configs(p.organization.org_uuid))
            .tap(self._announce)
        )

    async def _with_default_tenant(self, org: Organization) -> Result[tuple[Organization, Tenant], DomainError]:
        cmd = CreateTenant(org_uuid=org.org_uuid, tenant_code="default", tenant_name=f"{org.org_name} default")
        return (await self._tenants.create(cmd)).map(lambda tenant: (org, tenant))

    async def _with_admin_role(self, pair: tuple[Organization, Tenant]) -> Result[Provisioned, DomainError]:
        org, tenant = pair
        cmd = CreateRole(
            org_uuid=org.org_uuid,
            tenant_uuid=tenant.tenant_uuid,
            role_code="ORG_ADMIN",
            role_name="Organization administrator",
            role_type=RoleType.SYSTEM,
        )
        return (await self._roles.create(cmd)).map(lambda role: Provisioned(org, tenant, role))

    async def _seed_configs(self, org_uuid: str) -> Result[None, DomainError]:
        for key, value, value_type in DEFAULT_CONFIGS:
            cmd = CreateSysConfig(org_uuid=org_uuid, config_key=key, config_value=value, value_type=value_type)
            created = await self._configs.create(cmd)
            if isinstance(created, Error):
                return Error(created.error)
        return Ok(None)

    def _announce(self, p: Provisioned) -> None:
        self.publish_after_commit(
            [
                OrganizationProvisioned(
                    org_uuid=p.organization.org_uuid,
                    tenant_uuid=p.tenant.tenant_uuid,
                    admin_role_uuid=p.admin_role.role_uuid,
                )
            ]
        )


class OnboardingService(ApplicationService):
    def __init__(
        self,
        tx: TransactionManager,
        publisher: EventPublisher,
        employees: EmployeeService,
        users: UserService,
        new_id: IdGenerator = uuid_hex,
    ) -> None:
        super().__init__(tx, publisher, new_id)
        self._employees, self._users = employees, users

    @master
    async def onboard(
        self,
        employee: CreateEmployee,
        account: tuple[RegisterUser, PasswordHash, Iterable[RoleAssignment]] | None = None,
    ) -> Result[tuple[Employee, User | None], DomainError]:
        """hire (+ register login user + link) in ONE transaction."""
        hired = await self._employees.create(employee)
        if isinstance(hired, Error) or account is None:
            return hired.map(lambda e: (e, None))
        employee_uuid = hired.ok.employee_uuid
        cmd, password_hash, roles = account
        return await AsyncResult.of(self._users.register(cmd, password_hash, roles)).bind(
            lambda user: AsyncResult.of(
                self._employees.link_user(employee.org_uuid, employee_uuid, user.user_uuid)
            ).map(lambda emp: (emp, user))
        )
