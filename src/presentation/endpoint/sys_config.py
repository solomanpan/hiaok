from fastapi import APIRouter

from ..dependency import GetConfigByKeyDep, SysConfigCrudDep, WriteSubmitterDep, has_permission
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.sys_config import ConfigKeyRequest, SysConfigCreateRequest, SysConfigResponse, SysConfigUpdateRequest

router = APIRouter(prefix="/config", tags=["sys_config"])


@router.post("/add", dependencies=[has_permission("config:add")])
async def create_sys_config(
    request: ApiRequest[SysConfigCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("SysConfig", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list", dependencies=[has_permission("config:list")])
async def list_sys_configs(
    request: ApiRequest[OrgPageRequest], usecase: SysConfigCrudDep
) -> ApiResponse[PageResponse[SysConfigResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), SysConfigResponse.of))


@router.post("/get", dependencies=[has_permission("config:get")])
async def get_sys_config(request: ApiRequest[Keyed], usecase: SysConfigCrudDep) -> ApiResponse[SysConfigResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), SysConfigResponse.of)


@router.post("/update", dependencies=[has_permission("config:update")])
async def update_sys_config(
    request: ApiRequest[SysConfigUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(
        await submitter.update("SysConfig", request.request_id, info.org_uuid, info.uuid, info.to_command())
    )


@router.post("/delete", dependencies=[has_permission("config:delete")])
async def delete_sys_config(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("SysConfig", request.request_id, info.org_uuid, info.uuid))


@router.post("/get-by-key", dependencies=[has_permission("config:get-by-key")])
async def get_config_by_key(
    request: ApiRequest[ConfigKeyRequest], usecase: GetConfigByKeyDep
) -> ApiResponse[SysConfigResponse]:
    """Read-through Redis cache, evicted after every committed write (and by the SysConfigChanged event)."""
    info = request.req_info
    return reply(await usecase(info.org_uuid, info.config_key), SysConfigResponse.of)
