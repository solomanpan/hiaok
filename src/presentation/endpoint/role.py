from fastapi import APIRouter

from ...application.model import MenusPayload, PermissionsPayload
from ..dependency import RoleCrudDep, WriteSubmitterDep, has_permission
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.role import (
    AssignMenusRequest,
    GrantPermissionsRequest,
    RoleCreateRequest,
    RoleResponse,
    RoleUpdateRequest,
)

router = APIRouter(prefix="/role", tags=["role"])


@router.post("/add", dependencies=[has_permission("role:add")])
async def create_role(
    request: ApiRequest[RoleCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Role", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list", dependencies=[has_permission("role:list")])
async def list_roles(
    request: ApiRequest[OrgPageRequest], usecase: RoleCrudDep
) -> ApiResponse[PageResponse[RoleResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), RoleResponse.of))


@router.post("/get", dependencies=[has_permission("role:get")])
async def get_role(request: ApiRequest[Keyed], usecase: RoleCrudDep) -> ApiResponse[RoleResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), RoleResponse.of)


@router.post("/update", dependencies=[has_permission("role:update")])
async def update_role(
    request: ApiRequest[RoleUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.update("Role", request.request_id, info.org_uuid, info.uuid, info.to_command()))


@router.post("/delete", dependencies=[has_permission("role:delete")])
async def delete_role(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("Role", request.request_id, info.org_uuid, info.uuid))


@router.post("/grant-permissions", dependencies=[has_permission("role:grant-permissions")])
async def grant_role_permissions(
    request: ApiRequest[GrantPermissionsRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    """Replaces the role's permission set (removed ones are soft-deleted)."""
    info = request.req_info
    return accepted(
        await submitter.act(
            "Role",
            "grant_permissions",
            request.request_id,
            info.org_uuid,
            info.uuid,
            PermissionsPayload(tuple(info.permission_uuids)),
        )
    )


@router.post("/assign-menus", dependencies=[has_permission("role:assign-menus")])
async def assign_role_menus(
    request: ApiRequest[AssignMenusRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(
        await submitter.act(
            "Role", "assign_menus", request.request_id, info.org_uuid, info.uuid, MenusPayload(tuple(info.menu_uuids))
        )
    )
