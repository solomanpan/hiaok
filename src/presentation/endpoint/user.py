from fastapi import APIRouter

from ..dependency import (
    AssignUserRolesDep,
    ChangePasswordDep,
    GetUserAuthoritiesDep,
    RegisterUserDep,
    UserCrudDep,
)
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
    request: ApiRequest[UserRegisterRequest], usercase: RegisterUserDep
) -> ApiResponse[UserResponse]:
    return reply(await usercase(request.req_info.to_command()), UserResponse.of)


@router.post("/list")
async def list_users(
    request: ApiRequest[OrgPageRequest], usercase: UserCrudDep
) -> ApiResponse[PageResponse[UserResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), UserResponse.of))


@router.post("/get")
async def get_user(request: ApiRequest[Keyed], usercase: UserCrudDep) -> ApiResponse[UserResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), UserResponse.of)


@router.post("/update")
async def update_user(request: ApiRequest[UserUpdateRequest], usercase: UserCrudDep) -> ApiResponse[UserResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), UserResponse.of)


@router.post("/delete")
async def delete_user(request: ApiRequest[Keyed], usercase: UserCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))


@router.post("/assign-roles")
async def assign_roles(
    request: ApiRequest[AssignRolesRequest], usercase: AssignUserRolesDep
) -> ApiResponse[UserResponse]:
    info = request.req_info
    return reply(
        await usercase(info.org_uuid, info.uuid, [role.to_model() for role in info.roles]),
        UserResponse.of,
    )


@router.post("/change-password")
async def change_password(request: ApiRequest[ChangePasswordRequest], usercase: ChangePasswordDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase(info.org_uuid, info.uuid, info.new_password))


@router.post("/authorities")
async def user_authorities(
    request: ApiRequest[UserAuthoritiesRequest], usercase: GetUserAuthoritiesDep
) -> ApiResponse[AuthorityResponse]:
    """Effective role codes, permission codes and menu tree (union over enabled roles)."""
    info = request.req_info
    return reply(
        await usercase(info.org_uuid, info.uuid, info.project_uuid),
        AuthorityResponse.of,
    )
