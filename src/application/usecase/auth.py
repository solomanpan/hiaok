"""Authentication: login (credentials -> token) and resolving a session into a ``Principal``."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError
from hiaok_core.facade import PasswordHasher
from hiaok_core.fp import curry

from ..model import AuthorityModel, GrantedAuthorities, LoginCommand, LoginResult, Principal, Session
from ..service import AuthService, TenantService, UserService
from .errors import UseCaseErrors

type AuthoritiesOf = Callable[[str, str, str | None], Awaitable[Result[AuthorityModel, DomainError]]]


@curry
async def login(
    users: UserService, tenants: TenantService, hasher: PasswordHasher, auth: AuthService, cmd: LoginCommand
) -> Result[LoginResult, DomainError]:
    """username + password -> enabled user in an active tenant -> token.

    Unknown user and wrong password answer identically (and cost the same hashing) so usernames cannot be probed.
    """
    found = await users.find_by_username(cmd.org_uuid, cmd.tenant_uuid, cmd.username)
    if found.is_none():
        hasher.hash(cmd.password)
        return UseCaseErrors.invalid_credentials.err()
    user = found.value
    if not hasher.verify(cmd.password, user.password_hash.value):
        return UseCaseErrors.invalid_credentials.err()
    if not user.enabled:
        return UseCaseErrors.user_disabled.err(user_uuid=user.user_uuid)
    tenant = (await tenants.get(cmd.org_uuid, cmd.tenant_uuid)).bind(lambda t: t.ensure_active(datetime.now(UTC)))
    if isinstance(tenant, Error):
        return Error(tenant.error)
    token = await auth.issue(Session(user.user_uuid, cmd.org_uuid, cmd.tenant_uuid))
    return Ok(LoginResult(token, auth.session_ttl, user.user_uuid))


@curry
async def load_principal(
    auth: AuthService, authorities: AuthoritiesOf, session: Session
) -> Result[Principal, DomainError]:
    """Cached roles/permissions, or computed once (user -> roles -> permissions) and cached."""
    cached = await auth.cached_authorities(session.org_uuid, session.user_uuid)
    if cached.is_some():
        return Ok(Principal.of(session, cached.value))
    resolved = await authorities(session.org_uuid, session.user_uuid, None)
    if isinstance(resolved, Error):
        return Error(resolved.error)
    granted = GrantedAuthorities(tuple(resolved.ok.role_codes), tuple(resolved.ok.permission_codes))
    await auth.cache_authorities(session.org_uuid, session.user_uuid, granted)
    return Ok(Principal.of(session, granted))
