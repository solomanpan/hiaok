from fastapi import APIRouter

from ...application.model import OrgDetailModel
from ..dependency import OrganizationCrudDep, WriteSubmitterDep, has_permission
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import OrgScoped, PageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.organization import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationUpdateRequest,
    OrgDetailUpdateRequest,
)

router = APIRouter(prefix="/organization", tags=["organization"])


@router.post("/add", dependencies=[has_permission("organization:add")])
async def provision_organization(
    request: ApiRequest[OrganizationCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    """Creates the organization + detail + default tenant + ORG_ADMIN role + default configs atomically.

    ``resultInfo.uuid`` is the new organization's uuid (= ``orgUuid`` of every later call).
    """
    return accepted(await submitter.create("Organization", request.request_id, None, request.req_info.to_command()))


@router.post("/list", dependencies=[has_permission("organization:list")])
async def list_organizations(
    request: ApiRequest[PageRequest], usecase: OrganizationCrudDep
) -> ApiResponse[PageResponse[OrganizationResponse]]:
    return ApiResponse.ok(PageResponse.of(await usecase.list(None, request.req_info.query), OrganizationResponse.of))


@router.post("/get", dependencies=[has_permission("organization:get")])
async def get_organization(
    request: ApiRequest[OrgScoped], usecase: OrganizationCrudDep
) -> ApiResponse[OrganizationResponse]:
    org = request.req_info.org_uuid
    return reply(await usecase.get(org, org), OrganizationResponse.of)


@router.post("/update", dependencies=[has_permission("organization:update")])
async def update_organization(
    request: ApiRequest[OrganizationUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(
        await submitter.update("Organization", request.request_id, info.org_uuid, info.org_uuid, info.to_command())
    )


@router.post("/update-detail", dependencies=[has_permission("organization:update-detail")])
async def update_org_detail(
    request: ApiRequest[OrgDetailUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    detail: OrgDetailModel = info.to_model()
    return accepted(
        await submitter.act("Organization", "update_detail", request.request_id, info.org_uuid, info.org_uuid, detail)
    )


@router.post("/delete", dependencies=[has_permission("organization:delete")])
async def delete_organization(
    request: ApiRequest[OrgScoped], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    org = request.req_info.org_uuid
    return accepted(await submitter.delete("Organization", request.request_id, org, org))
