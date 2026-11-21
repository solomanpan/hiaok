from fastapi import APIRouter

from ..dependency import PermissionCrudDep, WriteSubmitterDep, has_permission
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.permission import PermissionCreateRequest, PermissionResponse, PermissionUpdateRequest

router = APIRouter(prefix="/permission", tags=["permission"])


@router.post("/add", dependencies=[has_permission("permission:add")])
async def create_permission(
    request: ApiRequest[PermissionCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Permission", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list", dependencies=[has_permission("permission:list")])
async def list_permissions(
    request: ApiRequest[OrgPageRequest], usecase: PermissionCrudDep
) -> ApiResponse[PageResponse[PermissionResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), PermissionResponse.of))


@router.post("/get", dependencies=[has_permission("permission:get")])
async def get_permission(request: ApiRequest[Keyed], usecase: PermissionCrudDep) -> ApiResponse[PermissionResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), PermissionResponse.of)


@router.post("/update", dependencies=[has_permission("permission:update")])
async def update_permission(
    request: ApiRequest[PermissionUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(
        await submitter.update("Permission", request.request_id, info.org_uuid, info.uuid, info.to_command())
    )


@router.post("/delete", dependencies=[has_permission("permission:delete")])
async def delete_permission(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("Permission", request.request_id, info.org_uuid, info.uuid))
