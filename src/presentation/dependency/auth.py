"""Authentication and authorization dependencies.

    @router.post("/add", dependencies=[has_permission("role:add")])      # any of the codes; ``role:*`` = all
    @router.post("/list", dependencies=[has_role("admin", "auditor")])   # any of the roles
    async def f(principal: PrincipalDep): ...                            # who is calling

A guard answers 401 (no valid token), 403 ``permission_denied`` / ``role_denied``, or 403 ``org_mismatch`` when the
body targets another organization than the caller's (unless the caller belongs to ``AUTH_PLATFORM_ORG_UUID``).
With ``AUTH_ENABLED=false`` every guard lets the call through.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated, Any

from expression import Error, Result
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from hiaok_core.context import current_context
from hiaok_core.exception import DomainError

from ...application.model import LoginCommand, LoginResult, Principal, Session
from ...application.service import AuthService
from ...application.usecase import auth as auth_uc
from ..security import SecurityErrors, Unauthenticated, auth_service
from .resources import ResourcesDep
from .service import TenantServiceDep, UserServiceDep
from .usecase import GetUserAuthoritiesDep

# ``auto_error=False``: a missing token is answered by us (envelope, code 401); the scheme puts "Authorize" in Swagger
_bearer = HTTPBearer(auto_error=False, description="Token from POST /auth/login")
BearerDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]

SYSTEM = Principal("system", "", "", frozenset(), frozenset({"*"}))

type Login = Callable[[LoginCommand], Awaitable[Result[LoginResult, DomainError]]]


def get_auth_service(r: ResourcesDep) -> AuthService:
    return auth_service(r)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_login(users: UserServiceDep, tenants: TenantServiceDep, r: ResourcesDep, auth: AuthServiceDep) -> Login:
    return auth_uc.login(users, tenants, r.hasher, auth)


LoginDep = Annotated[Login, Depends(get_login)]


async def get_principal(
    r: ResourcesDep, auth: AuthServiceDep, authorities: GetUserAuthoritiesDep, _: BearerDep
) -> Principal:
    """The caller, from the context the middleware filled in from the token."""
    if not r.settings.auth.enabled:
        return SYSTEM
    ctx = current_context()
    if ctx.user_uuid is None or ctx.org_uuid is None:
        raise Unauthenticated
    session = Session(ctx.user_uuid, ctx.org_uuid, ctx.tenant_uuid or "")
    loaded = await auth_uc.load_principal(auth, authorities, session)
    if isinstance(loaded, Error):  # the account was deleted or disabled after the token was issued
        raise Unauthenticated
    return loaded.ok


PrincipalDep = Annotated[Principal, Depends(get_principal)]


async def _target_org(request: Request) -> str | None:
    """``reqInfo.orgUuid`` of the body (the body is cached, the endpoint still reads it)."""
    try:
        body: Any = await request.json()
    except ValueError:
        return None
    info = body.get("reqInfo") if isinstance(body, dict) else None
    org = info.get("orgUuid") if isinstance(info, dict) else None
    return org if isinstance(org, str) else None


async def _ensure_org(request: Request, r: ResourcesDep, principal: Principal) -> None:
    platform = r.settings.auth.platform_org_uuid
    if principal.is_superuser or (platform is not None and principal.org_uuid == platform):
        return
    org = await _target_org(request)
    if org is not None and org != principal.org_uuid:
        SecurityErrors.org_mismatch.raise_(org_uuid=org)


GUARD_ATTRIBUTE = "__hiaok_guard__"  # architecture test: every protected route carries one


def _guard(check: Callable[..., Awaitable[Principal]]) -> Any:
    setattr(check, GUARD_ATTRIBUTE, True)
    return Depends(check)


def authenticated() -> Any:
    """Any logged-in user."""

    async def check(request: Request, r: ResourcesDep, principal: PrincipalDep) -> Principal:
        await _ensure_org(request, r, principal)
        return principal

    return _guard(check)


def has_permission(*required: str) -> Any:
    """Any of the permission codes (``role:*`` covers ``role:add``, ``*`` covers everything)."""

    async def check(request: Request, r: ResourcesDep, principal: PrincipalDep) -> Principal:
        if not principal.has_permission(*required):
            SecurityErrors.permission_denied.raise_(required=" | ".join(required))
        await _ensure_org(request, r, principal)
        return principal

    return _guard(check)


def has_role(*required: str) -> Any:
    """Any of the role codes."""

    async def check(request: Request, r: ResourcesDep, principal: PrincipalDep) -> Principal:
        if not principal.has_role(*required):
            SecurityErrors.role_denied.raise_(required=" | ".join(required))
        await _ensure_org(request, r, principal)
        return principal

    return _guard(check)
