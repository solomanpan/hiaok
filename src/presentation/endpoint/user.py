from expression import Error
from fastapi import APIRouter

from ...application.model import RolesPayload
from ..dependency import (
    CaptchaGuardDep,
    ChangePasswordDep,
    GetUserAuthoritiesDep,
    OptionalPrincipalDep,
    RegisterUserDep,
    UserCrudDep,
    WriteSubmitterDep,
    has_permission,
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
from ..security import SecurityErrors

router = APIRouter(prefix="/user", tags=["user"])


@router.post("/register")
async def register_user(
    request: ApiRequest[UserRegisterRequest],
    usecase: RegisterUserDep,
    captcha_guard: CaptchaGuardDep,
    caller: OptionalPrincipalDep,
) -> ApiResponse[UserResponse]:
    """Registers a user; needs a solved captcha (``captchaId`` / ``captchaCode``) when captcha is switched on.

    Anyone may sign up, but only a caller holding ``user:assign-roles`` may attach ``roleUuids``.
    """
    if request.req_info.role_uuids and not (caller and caller.has_permission("user:assign-roles")):
        SecurityErrors.permission_denied.raise_(required="user:assign-roles")
    checked = await captcha_guard(request.req_info.captcha_id, request.req_info.captcha_code)
    if isinstance(checked, Error):
        return reply(checked, lambda _: None)  # type: ignore[return-value]
    return reply(await usecase(request.req_info.to_command()), UserResponse.of)


@router.post("/list", dependencies=[has_permission("user:list")])
async def list_users(
    request: ApiRequest[OrgPageRequest], usecase: UserCrudDep
) -> ApiResponse[PageResponse[UserResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), UserResponse.of))


@router.post("/get", dependencies=[has_permission("user:get")])
async def get_user(request: ApiRequest[Keyed], usecase: UserCrudDep) -> ApiResponse[UserResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), UserResponse.of)


@router.post("/update", dependencies=[has_permission("user:update")])
async def update_user(
    request: ApiRequest[UserUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.update("User", request.request_id, info.org_uuid, info.uuid, info.to_command()))


@router.post("/delete", dependencies=[has_permission("user:delete")])
async def delete_user(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("User", request.request_id, info.org_uuid, info.uuid))


@router.post("/assign-roles", dependencies=[has_permission("user:assign-roles")])
async def assign_roles(
    request: ApiRequest[AssignRolesRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    payload = RolesPayload(tuple(role.to_model() for role in info.roles))
    return accepted(await submitter.act("User", "assign_roles", request.request_id, info.org_uuid, info.uuid, payload))


@router.post("/change-password", dependencies=[has_permission("user:change-password")])
async def change_password(request: ApiRequest[ChangePasswordRequest], usecase: ChangePasswordDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usecase(info.org_uuid, info.uuid, info.new_password))


@router.post("/authorities", dependencies=[has_permission("user:authorities")])
async def user_authorities(
    request: ApiRequest[UserAuthoritiesRequest], usecase: GetUserAuthoritiesDep
) -> ApiResponse[AuthorityResponse]:
    """Effective role codes, permission codes and menu tree (union over enabled roles)."""
    info = request.req_info
    return reply(
        await usecase(info.org_uuid, info.uuid, info.project_uuid),
        AuthorityResponse.of,
    )
