from expression import Error
from fastapi import APIRouter

from ..dependency import AuthServiceDep, BearerDep, GetUserAuthoritiesDep, LoginDep, PrincipalDep, authenticated
from ..dependency.auth import SYSTEM
from ..schema.auth import EmptyRequest, LoginRequest, LoginResponse, PrincipalResponse
from ..schema.envelope import UNAUTHENTICATED, ApiRequest, ApiResponse, reply
from ..security import Unauthenticated

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(request: ApiRequest[LoginRequest], usecase: LoginDep) -> ApiResponse[LoginResponse]:
    """Username + password -> bearer token (send it as ``Authorization: Bearer <token>``)."""
    result = await usecase(request.req_info.to_command())
    if isinstance(result, Error) and result.error.code == "invalid_credentials":
        return ApiResponse[LoginResponse].fail(UNAUTHENTICATED, result.error.message, result.error.code)
    return reply(result, LoginResponse.of)


@router.post("/logout", dependencies=[authenticated()])
async def logout(request: ApiRequest[EmptyRequest], auth: AuthServiceDep, credentials: BearerDep) -> ApiResponse[None]:
    """Invalidates the token of this call."""
    if credentials is None:
        raise Unauthenticated
    await auth.revoke(credentials.credentials)
    return ApiResponse[None].ok(None)


@router.post("/me", dependencies=[authenticated()])
async def me(
    request: ApiRequest[EmptyRequest], principal: PrincipalDep, authorities: GetUserAuthoritiesDep
) -> ApiResponse[PrincipalResponse]:
    """Who am I: user, organization, tenant, the effective role / permission codes and the visible menu tree.

    The menu tree only decides what the front end shows; every API call is still checked by its own guard.
    """
    if principal.is_superuser and principal.user_uuid == SYSTEM.user_uuid:  # authentication is off
        return ApiResponse.ok(PrincipalResponse.of(principal))
    result = await authorities(principal.org_uuid, principal.user_uuid, None)
    return reply(result, lambda authority: PrincipalResponse.of(principal, authority))
