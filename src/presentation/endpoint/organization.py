from fastapi import APIRouter

from ..dependency import OrganizationCrudDep, ProvisionOrganizationDep, UpdateOrgDetailDep
from ..schema.common import OrgScoped, PageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.organization import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    OrgDetailUpdateRequest,
)

router = APIRouter(prefix="/organization", tags=["organization"])


@router.post("/add")
async def provision_organization(
    request: ApiRequest[OrganizationCreateRequest], usercase: ProvisionOrganizationDep
) -> ApiResponse[OrganizationResponse]:
    """Creates the organization + detail + default tenant + ORG_ADMIN role + default configs atomically."""
    return reply(await usercase(request.req_info.to_command()), OrganizationResponse.of)


@router.post("/list")
async def list_organizations(
    request: ApiRequest[PageRequest], usercase: OrganizationCrudDep
) -> ApiResponse[PageResponse[OrganizationResponse]]:
    return ApiResponse.ok(PageResponse.of(await usercase.list(None, request.req_info.query), OrganizationResponse.of))


@router.post("/get")
async def get_organization(
    request: ApiRequest[OrgScoped], usercase: OrganizationCrudDep
) -> ApiResponse[OrganizationResponse]:
    org = request.req_info.org_uuid
    return reply(await usercase.get(org, org), OrganizationResponse.of)


@router.post("/update")
async def update_organization(
    request: ApiRequest[OrganizationUpdateRequest], usercase: OrganizationCrudDep
) -> ApiResponse[OrganizationResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.org_uuid, info.to_command()), OrganizationResponse.of)


@router.post("/update-detail")
async def update_org_detail(
    request: ApiRequest[OrgDetailUpdateRequest], usercase: UpdateOrgDetailDep
) -> ApiResponse[OrganizationResponse]:
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.to_model()), OrganizationResponse.of)


@router.post("/delete")
async def delete_organization(request: ApiRequest[OrgScoped], usercase: OrganizationCrudDep) -> ApiResponse[None]:
    org = request.req_info.org_uuid
    return done(await usercase.delete(org, org))
