from fastapi import APIRouter

from ..dependency import TenantCrudDep, WriteSubmitterDep
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.tenant import TenantCreateRequest, TenantResponse, TenantUpdateRequest

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.post("/add")
async def create_tenant(
    request: ApiRequest[TenantCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Tenant", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list")
async def list_tenants(
    request: ApiRequest[OrgPageRequest], usecase: TenantCrudDep
) -> ApiResponse[PageResponse[TenantResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), TenantResponse.of))


@router.post("/get")
async def get_tenant(request: ApiRequest[Keyed], usecase: TenantCrudDep) -> ApiResponse[TenantResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), TenantResponse.of)


@router.post("/update")
async def update_tenant(
    request: ApiRequest[TenantUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.update("Tenant", request.request_id, info.org_uuid, info.uuid, info.to_command()))


@router.post("/delete")
async def delete_tenant(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("Tenant", request.request_id, info.org_uuid, info.uuid))
