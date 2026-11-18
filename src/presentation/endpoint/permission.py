from fastapi import APIRouter

from ..dependency import PermissionCrudDep
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.permission import PermissionCreateRequest, PermissionResponse, PermissionUpdateRequest

router = APIRouter(prefix="/permission", tags=["permission"])


@router.post("/add")
async def create_permission(
    request: ApiRequest[PermissionCreateRequest], usercase: PermissionCrudDep
) -> ApiResponse[PermissionResponse]:
    return reply(await usercase.create(request.req_info.to_command()), PermissionResponse.of)


@router.post("/list")
async def list_permissions(
    request: ApiRequest[OrgPageRequest], usercase: PermissionCrudDep
) -> ApiResponse[PageResponse[PermissionResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), PermissionResponse.of))


@router.post("/get")
async def get_permission(request: ApiRequest[Keyed], usercase: PermissionCrudDep) -> ApiResponse[PermissionResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), PermissionResponse.of)


@router.post("/update")
async def update_permission(
    request: ApiRequest[PermissionUpdateRequest], usercase: PermissionCrudDep
) -> ApiResponse[PermissionResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), PermissionResponse.of)


@router.post("/delete")
async def delete_permission(request: ApiRequest[Keyed], usercase: PermissionCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))
