from fastapi import APIRouter

from ..dependency import TenantCrudDep
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.tenant import TenantCreateRequest, TenantResponse, TenantUpdateRequest

router = APIRouter(prefix="/tenant", tags=["tenant"])


@router.post("/add")
async def create_tenant(
    request: ApiRequest[TenantCreateRequest], usercase: TenantCrudDep
) -> ApiResponse[TenantResponse]:
    return reply(await usercase.create(request.req_info.to_command()), TenantResponse.of)


@router.post("/list")
async def list_tenants(
    request: ApiRequest[OrgPageRequest], usercase: TenantCrudDep
) -> ApiResponse[PageResponse[TenantResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), TenantResponse.of))


@router.post("/get")
async def get_tenant(request: ApiRequest[Keyed], usercase: TenantCrudDep) -> ApiResponse[TenantResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), TenantResponse.of)


@router.post("/update")
async def update_tenant(
    request: ApiRequest[TenantUpdateRequest], usercase: TenantCrudDep
) -> ApiResponse[TenantResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), TenantResponse.of)


@router.post("/delete")
async def delete_tenant(request: ApiRequest[Keyed], usercase: TenantCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))
