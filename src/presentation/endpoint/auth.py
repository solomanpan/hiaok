from expression import Error
from fastapi import APIRouter

from ..captcha import data_uri, render_svg
from ..dependency import (
    AuthServiceDep,
    BearerDep,
    CaptchaGuardDep,
    CaptchaServiceDep,
    GetUserAuthoritiesDep,
    LoginDep,
    PrincipalDep,
    authenticated,
)
from ..dependency.auth import SYSTEM
from ..schema.auth import CaptchaResponse, EmptyRequest, LoginRequest, LoginResponse, PrincipalResponse
from ..schema.envelope import UNAUTHENTICATED, ApiRequest, ApiResponse, reply
from ..security import Unauthenticated

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/captcha")
async def captcha(
    request: ApiRequest[EmptyRequest], service: CaptchaServiceDep, guard: CaptchaGuardDep
) -> ApiResponse[CaptchaResponse]:
    """A new one-time captcha image for login / register. ``required: false`` when captcha is switched off."""
    if not guard.enabled:
        return ApiResponse.ok(CaptchaResponse(required=False))
    captcha_id, code = await service.issue()
    return ApiResponse.ok(
        CaptchaResponse(
            required=True, captcha_id=captcha_id, image=data_uri(render_svg(code)), expires_in=service.ttl_seconds
        )
    )


@router.post("/login")
async def login(
    request: ApiRequest[LoginRequest], usecase: LoginDep, captcha_guard: CaptchaGuardDep
) -> ApiResponse[LoginResponse]:
    """Username + password (+ captcha when required) -> bearer token (``Authorization: Bearer <token>``)."""
    checked = await captcha_guard(request.req_info.captcha_id, request.req_info.captcha_code)
    if isinstance(checked, Error):
        return reply(checked, lambda _: None)  # type: ignore[return-value]
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
