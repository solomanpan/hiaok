from fastapi import APIRouter, status

from ..dependency import OrganizationCrudDep, PageDep, ProvisionOrganizationDep, UpdateOrgDetailDep
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.organization import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    OrgDetailDTO,
)

router = APIRouter(prefix="/orgs", tags=["organization"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def provision_organization(body: OrganizationCreateRequest, uc: ProvisionOrganizationDep) -> OrganizationResponse:
    """Creates the organization + detail + default tenant + ORG_ADMIN role + default configs atomically."""
    return unwrap(await uc(body.to_command()), OrganizationResponse.of)


@router.get("")
async def list_organizations(page: PageDep, uc: OrganizationCrudDep) -> PageResponse[OrganizationResponse]:
    return PageResponse.of(await uc.list(None, page), OrganizationResponse.of)


@router.get("/{org_uuid}")
async def get_organization(org_uuid: str, uc: OrganizationCrudDep) -> OrganizationResponse:
    return unwrap(await uc.get(org_uuid, org_uuid), OrganizationResponse.of)


@router.patch("/{org_uuid}")
async def update_organization(
    org_uuid: str, body: OrganizationUpdateRequest, uc: OrganizationCrudDep
) -> OrganizationResponse:
    return unwrap(await uc.update(org_uuid, org_uuid, body.to_command()), OrganizationResponse.of)


@router.put("/{org_uuid}/detail")
async def update_org_detail(org_uuid: str, body: OrgDetailDTO, uc: UpdateOrgDetailDep) -> OrganizationResponse:
    return unwrap(await uc(org_uuid, body.to_model()), OrganizationResponse.of)


@router.delete("/{org_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(org_uuid: str, uc: OrganizationCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, org_uuid), lambda _: None)
