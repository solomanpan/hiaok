from fastapi import APIRouter

from ...application.model import RolesPayload
from ..dependency import (
    ChangePasswordDep,
    GetUserAuthoritiesDep,
    RegisterUserDep,
    UserCrudDep,
    WriteSubmitterDep,
)
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.user import (
    AssignRolesRequest,
    AuthorityResponse,
    ChangePasswordRequest,
    UserAuthoritiesRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/register")
async def register_user(
    request: ApiRequest[UserRegisterRequest], usecase: RegisterUserDep
) -> ApiResponse[UserResponse]:
    return reply(await usecase(request.req_info.to_command()), UserResponse.of)


@router.post("/list")
async def list_users(
    request: ApiRequest[OrgPageRequest], usecase: UserCrudDep
) -> ApiResponse[PageResponse[UserResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), UserResponse.of))


@router.post("/get")
async def get_user(request: ApiRequest[Keyed], usecase: UserCrudDep) -> ApiResponse[UserResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), UserResponse.of)


@router.post("/update")
async def update_user(
    request: ApiRequest[UserUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.update("User", request.request_id, info.org_uuid, info.uuid, info.to_command()))


@router.post("/delete")
async def delete_user(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("User", request.request_id, info.org_uuid, info.uuid))


@router.post("/assign-roles")
async def assign_roles(
    request: ApiRequest[AssignRolesRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    payload = RolesPayload(tuple(role.to_model() for role in info.roles))
    return accepted(await submitter.act("User", "assign_roles", request.request_id, info.org_uuid, info.uuid, payload))


@router.post("/change-password")
async def change_password(request: ApiRequest[ChangePasswordRequest], usecase: ChangePasswordDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usecase(info.org_uuid, info.uuid, info.new_password))


@router.post("/authorities")
async def user_authorities(
    request: ApiRequest[UserAuthoritiesRequest], usecase: GetUserAuthoritiesDep
) -> ApiResponse[AuthorityResponse]:
    """Effective role codes, permission codes and menu tree (union over enabled roles)."""
    info = request.req_info
    return reply(
        await usecase(info.org_uuid, info.uuid, info.project_uuid),
        AuthorityResponse.of,
    )
