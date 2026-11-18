from fastapi import APIRouter, status

from ..dependency import GetConfigByKeyDep, PageDep, SysConfigCrudDep
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.sys_config import SysConfigCreateRequest, SysConfigResponse, SysConfigUpdateRequest

router = APIRouter(prefix="/orgs/{org_uuid}/configs", tags=["sys_config"])


@router.get("/key/{config_key}")
async def get_config_by_key(org_uuid: str, config_key: str, uc: GetConfigByKeyDep) -> SysConfigResponse:
    """Read-through Redis cache, evicted after every committed write (and by the SysConfigChanged event)."""
    return unwrap(await uc(org_uuid, config_key), SysConfigResponse.of)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_sys_config(org_uuid: str, body: SysConfigCreateRequest, uc: SysConfigCrudDep) -> SysConfigResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), SysConfigResponse.of)


@router.get("")
async def list_configs(org_uuid: str, page: PageDep, uc: SysConfigCrudDep) -> PageResponse[SysConfigResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), SysConfigResponse.of)


@router.get("/{config_uuid}")
async def get_sys_config(org_uuid: str, config_uuid: str, uc: SysConfigCrudDep) -> SysConfigResponse:
    return unwrap(await uc.get(org_uuid, config_uuid), SysConfigResponse.of)


@router.patch("/{config_uuid}")
async def update_sys_config(
    org_uuid: str, config_uuid: str, body: SysConfigUpdateRequest, uc: SysConfigCrudDep
) -> SysConfigResponse:
    return unwrap(await uc.update(org_uuid, config_uuid, body.to_command()), SysConfigResponse.of)


@router.delete("/{config_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sys_config(org_uuid: str, config_uuid: str, uc: SysConfigCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, config_uuid), lambda _: None)
