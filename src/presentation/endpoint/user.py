from fastapi import APIRouter, Query, status

from ..dependency import (
    AssignUserRolesDep,
    ChangePasswordDep,
    GetUserAuthoritiesDep,
    PageDep,
    RegisterUserDep,
    UserCrudDep,
)
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.user import (
    AssignRolesRequest,
    AuthorityResponse,
    ChangePasswordRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/orgs/{org_uuid}/users", tags=["user"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def register_user(org_uuid: str, body: UserRegisterRequest, uc: RegisterUserDep) -> UserResponse:
    """Password policy -> tenant active -> roles exist in the tenant -> hash -> user + user_detail + user_role."""
    return unwrap(await uc(body.to_command(org_uuid)), UserResponse.of)


@router.get("")
async def list_users(org_uuid: str, page: PageDep, uc: UserCrudDep) -> PageResponse[UserResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), UserResponse.of)


@router.get("/{user_uuid}")
async def get_user(org_uuid: str, user_uuid: str, uc: UserCrudDep) -> UserResponse:
    return unwrap(await uc.get(org_uuid, user_uuid), UserResponse.of)


@router.patch("/{user_uuid}")
async def update_user(org_uuid: str, user_uuid: str, body: UserUpdateRequest, uc: UserCrudDep) -> UserResponse:
    return unwrap(await uc.update(org_uuid, user_uuid, body.to_command()), UserResponse.of)


@router.delete("/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(org_uuid: str, user_uuid: str, uc: UserCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, user_uuid), lambda _: None)


@router.put("/{user_uuid}/roles")
async def assign_roles(org_uuid: str, user_uuid: str, body: AssignRolesRequest, uc: AssignUserRolesDep) -> UserResponse:
    return unwrap(await uc(org_uuid, user_uuid, [r.to_model() for r in body.roles]), UserResponse.of)


@router.put("/{user_uuid}/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(org_uuid: str, user_uuid: str, body: ChangePasswordRequest, uc: ChangePasswordDep) -> None:
    unwrap(await uc(org_uuid, user_uuid, body.new_password), lambda _: None)


@router.get("/{user_uuid}/authorities")
async def user_authorities(
    org_uuid: str,
    user_uuid: str,
    uc: GetUserAuthoritiesDep,
    project_uuid: str | None = Query(None, description="include roles granted inside this project"),
) -> AuthorityResponse:
    """Effective role codes, permission codes and menu tree (union over enabled roles)."""
    return unwrap(await uc(org_uuid, user_uuid, project_uuid), AuthorityResponse.of)
