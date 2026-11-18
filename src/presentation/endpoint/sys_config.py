from fastapi import APIRouter

from ..dependency import GetConfigByKeyDep, SysConfigCrudDep
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.sys_config import ConfigKeyRequest, SysConfigCreateRequest, SysConfigResponse, SysConfigUpdateRequest

router = APIRouter(prefix="/config", tags=["sys_config"])


@router.post("/add")
async def create_sys_config(
    request: ApiRequest[SysConfigCreateRequest], usercase: SysConfigCrudDep
) -> ApiResponse[SysConfigResponse]:
    return reply(await usercase.create(request.req_info.to_command()), SysConfigResponse.of)


@router.post("/list")
async def list_sys_configs(
    request: ApiRequest[OrgPageRequest], usercase: SysConfigCrudDep
) -> ApiResponse[PageResponse[SysConfigResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), SysConfigResponse.of))


@router.post("/get")
async def get_sys_config(request: ApiRequest[Keyed], usercase: SysConfigCrudDep) -> ApiResponse[SysConfigResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), SysConfigResponse.of)


@router.post("/update")
async def update_sys_config(
    request: ApiRequest[SysConfigUpdateRequest], usercase: SysConfigCrudDep
) -> ApiResponse[SysConfigResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), SysConfigResponse.of)


@router.post("/delete")
async def delete_sys_config(request: ApiRequest[Keyed], usercase: SysConfigCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))


@router.post("/get-by-key")
async def get_config_by_key(
    request: ApiRequest[ConfigKeyRequest], usercase: GetConfigByKeyDep
) -> ApiResponse[SysConfigResponse]:
    """Read-through Redis cache, evicted after every committed write (and by the SysConfigChanged event)."""
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.config_key), SysConfigResponse.of)
