from fastapi import APIRouter, status

from ..dependency import AssignRoleMenusDep, GrantRolePermissionsDep, PageDep, RoleCrudDep
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.role import (
    AssignMenusRequest,
    GrantPermissionsRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)

router = APIRouter(prefix="/orgs/{org_uuid}/roles", tags=["role"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_role(org_uuid: str, body: RoleCreateRequest, uc: RoleCrudDep) -> RoleResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), RoleResponse.of)


@router.get("")
async def list_roles(org_uuid: str, page: PageDep, uc: RoleCrudDep) -> PageResponse[RoleResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), RoleResponse.of)


@router.get("/{role_uuid}")
async def get_role(org_uuid: str, role_uuid: str, uc: RoleCrudDep) -> RoleResponse:
    return unwrap(await uc.get(org_uuid, role_uuid), RoleResponse.of)


@router.patch("/{role_uuid}")
async def update_role(org_uuid: str, role_uuid: str, body: RoleUpdateRequest, uc: RoleCrudDep) -> RoleResponse:
    return unwrap(await uc.update(org_uuid, role_uuid, body.to_command()), RoleResponse.of)


@router.delete("/{role_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(org_uuid: str, role_uuid: str, uc: RoleCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, role_uuid), lambda _: None)


@router.put("/{role_uuid}/permissions")
async def grant_role_permissions(
    org_uuid: str, role_uuid: str, body: GrantPermissionsRequest, uc: GrantRolePermissionsDep
) -> RoleResponse:
    """Replaces the role's permission set (role_permission rows are diffed, removed ones soft-deleted)."""
    return unwrap(await uc(org_uuid, role_uuid, body.permission_uuids), RoleResponse.of)


@router.put("/{role_uuid}/menus")
async def assign_role_menus(
    org_uuid: str, role_uuid: str, body: AssignMenusRequest, uc: AssignRoleMenusDep
) -> RoleResponse:
    return unwrap(await uc(org_uuid, role_uuid, body.menu_uuids), RoleResponse.of)
