from __future__ import annotations

from hiaok_core.fp import AsyncResult, curry

from ..model import CreateOrganization, OrganizationModel, OrgDetailModel
from ..service import OrganizationService, ProvisioningService


@curry
def provision_organization(provisioning: ProvisioningService, cmd: CreateOrganization):
    """One transaction: organization + detail + default tenant + ORG_ADMIN role + default configs."""
    return AsyncResult.of(provisioning.provision(cmd)).map(lambda p: OrganizationModel.from_domain(p.organization))


@curry
def update_org_detail(organizations: OrganizationService, org_uuid: str, detail: OrgDetailModel):
    return AsyncResult.of(organizations.update_detail(org_uuid, detail)).map(OrganizationModel.from_domain)
