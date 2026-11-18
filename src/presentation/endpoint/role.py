from fastapi import APIRouter

from ..dependency import AssignRoleMenusDep, GrantRolePermissionsDep, RoleCrudDep
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.role import (
    AssignMenusRequest,
    GrantPermissionsRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)

router = APIRouter(prefix="/role", tags=["role"])


@router.post("/add")
async def create_role(request: ApiRequest[RoleCreateRequest], usercase: RoleCrudDep) -> ApiResponse[RoleResponse]:
    return reply(await usercase.create(request.req_info.to_command()), RoleResponse.of)


@router.post("/list")
async def list_roles(
    request: ApiRequest[OrgPageRequest], usercase: RoleCrudDep
) -> ApiResponse[PageResponse[RoleResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), RoleResponse.of))


@router.post("/get")
async def get_role(request: ApiRequest[Keyed], usercase: RoleCrudDep) -> ApiResponse[RoleResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), RoleResponse.of)


@router.post("/update")
async def update_role(request: ApiRequest[RoleUpdateRequest], usercase: RoleCrudDep) -> ApiResponse[RoleResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), RoleResponse.of)


@router.post("/delete")
async def delete_role(request: ApiRequest[Keyed], usercase: RoleCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))


@router.post("/grant-permissions")
async def grant_role_permissions(
    request: ApiRequest[GrantPermissionsRequest], usercase: GrantRolePermissionsDep
) -> ApiResponse[RoleResponse]:
    """Replaces the role's permission set (role_permission rows are diffed, removed ones soft-deleted)."""
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.uuid, info.permission_uuids), RoleResponse.of)


@router.post("/assign-menus")
async def assign_role_menus(
    request: ApiRequest[AssignMenusRequest], usercase: AssignRoleMenusDep
) -> ApiResponse[RoleResponse]:
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.uuid, info.menu_uuids), RoleResponse.of)
