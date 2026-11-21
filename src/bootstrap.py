"""``hiaok bootstrap``: create an organization and its first administrator with authentication left ON.

    hiaok bootstrap --org-code ACME --org-name "Acme" --username admin [--password ...]

One transaction: organization + default tenant + ``ORG_ADMIN`` role (one wildcard per resource) + default configs
(``ProvisioningService``) + a user holding that role (``register_user``). Any failure rolls everything back, so a
half-provisioned organization without an administrator cannot be left behind. The password comes from
``--password``, else ``HIAOK_ADMIN_PASSWORD``, else it is generated and printed once.
"""

from __future__ import annotations

import argparse
import os
import secrets
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from expression import Error, Result
from hiaok_core.exception import DomainError
from hiaok_core.facade import DataSource, TransactionManager
from hiaok_core.fp import AsyncResult

from .application.model import CreateOrganization, RegisterUser, UserModel
from .application.service import Provisioned

type Provision = Callable[[CreateOrganization], Awaitable[Result[Provisioned, DomainError]]]
type Register = Callable[[RegisterUser], Awaitable[Result[UserModel, DomainError]]]


@dataclass(frozen=True)
class Bootstrapped:
    org_uuid: str
    tenant_uuid: str
    role_uuid: str
    user_uuid: str
    username: str


async def bootstrap(
    tx: TransactionManager,
    provision: Provision,
    register: Register,
    *,
    org_code: str,
    org_name: str,
    username: str,
    password: str,
) -> Result[Bootstrapped, DomainError]:
    """Provision the organization and register its administrator in ONE master transaction."""

    def administrator(p: Provisioned) -> AsyncResult[Bootstrapped, DomainError]:
        cmd = RegisterUser(
            org_uuid=p.organization.org_uuid,
            tenant_uuid=p.tenant.tenant_uuid,
            username=username,
            password=password,
            role_uuids=(p.admin_role.role_uuid,),
        )
        return AsyncResult.of(register(cmd)).map(
            lambda user: Bootstrapped(
                p.organization.org_uuid, p.tenant.tenant_uuid, p.admin_role.role_uuid, user.user_uuid, username
            )
        )

    async with tx.begin(DataSource.MASTER) as t:  # the services' @master methods join this scope
        result = await AsyncResult.of(provision(CreateOrganization(org_code=org_code, org_name=org_name))).bind(
            administrator
        )
        if isinstance(result, Error):
            t.set_rollback_only()
        return result


def _parse(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="hiaok bootstrap", description="Create an organization and its administrator.")
    p.add_argument("--org-code", required=True)
    p.add_argument("--org-name", required=True)
    p.add_argument("--username", default="admin")
    p.add_argument("--password", help="default: $HIAOK_ADMIN_PASSWORD, else generated and printed once")
    return p.parse_args(argv)


async def run_bootstrap(argv: list[str]) -> int:
    from .application.config import get_settings
    from .application.usecase import user as user_uc
    from .infrastructure.resources import build_resources, open_resources
    from .presentation.dependency.service import (
        get_organization_service,
        get_permission_service,
        get_provisioning_service,
        get_role_service,
        get_sys_config_service,
        get_tenant_service,
        get_user_service,
    )

    args = _parse(argv)
    given = args.password or os.environ.get("HIAOK_ADMIN_PASSWORD")
    password = given or secrets.token_urlsafe(12)

    resources = build_resources(get_settings())
    async with open_resources(resources) as r:
        tenants, roles = get_tenant_service(r), get_role_service(r)
        provisioning = get_provisioning_service(
            r, get_organization_service(r), tenants, roles, get_sys_config_service(r), get_permission_service(r)
        )
        register = user_uc.register_user(get_user_service(r), tenants, roles, r.hasher)
        result = await bootstrap(
            r.tx,
            provisioning.provision,
            register,
            org_code=args.org_code,
            org_name=args.org_name,
            username=args.username,
            password=password,
        )

    if isinstance(result, Error):
        print(f"bootstrap failed: {result.error.code}: {result.error.message}", file=sys.stderr)
        return 1
    b = result.ok
    print(f"organization  {args.org_code}  orgUuid={b.org_uuid}")
    print(f"tenant        default  tenantUuid={b.tenant_uuid}")
    print(f"administrator {b.username}  userUuid={b.user_uuid}  role=ORG_ADMIN")
    if not given:
        print(f"password      {password}   (shown once: sign in and change it)")
    print(f"optional: AUTH_PLATFORM_ORG_UUID={b.org_uuid} lets this organization manage every organization")
    return 0
