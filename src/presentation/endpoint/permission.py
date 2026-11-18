from fastapi import APIRouter, status

from ..dependency import PageDep, PermissionCrudDep
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.permission import PermissionCreateRequest, PermissionResponse, PermissionUpdateRequest

router = APIRouter(prefix="/orgs/{org_uuid}/permissions", tags=["permission"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_permission(org_uuid: str, body: PermissionCreateRequest, uc: PermissionCrudDep) -> PermissionResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), PermissionResponse.of)


@router.get("")
async def list_permissions(org_uuid: str, page: PageDep, uc: PermissionCrudDep) -> PageResponse[PermissionResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), PermissionResponse.of)


@router.get("/{permission_uuid}")
async def get_permission(org_uuid: str, permission_uuid: str, uc: PermissionCrudDep) -> PermissionResponse:
    return unwrap(await uc.get(org_uuid, permission_uuid), PermissionResponse.of)


@router.patch("/{permission_uuid}")
async def update_permission(
    org_uuid: str, permission_uuid: str, body: PermissionUpdateRequest, uc: PermissionCrudDep
) -> PermissionResponse:
    return unwrap(await uc.update(org_uuid, permission_uuid, body.to_command()), PermissionResponse.of)


@router.delete("/{permission_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_permission(org_uuid: str, permission_uuid: str, uc: PermissionCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, permission_uuid), lambda _: None)
