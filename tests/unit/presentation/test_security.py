"""Login token -> principal -> guards, and the rule that new routes cannot silently skip authorization."""

from __future__ import annotations

import asyncio
import importlib
import pkgutil
from types import SimpleNamespace
from typing import Any, cast

import pytest
from expression import Error, Ok, Some, option
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from src.application.config import AppConfig, AuthConfig, Settings
from src.application.model import AuthorityModel, GrantedAuthorities, LoginCommand, Principal, Session
from src.application.service import AuthService
from src.application.usecase import auth as auth_uc
from src.infrastructure.cache.memory_cache import InMemoryCache
from src.infrastructure.resources import build_resources
from src.presentation import endpoint
from src.presentation.dependency import PrincipalDep, authenticated, has_permission, has_role
from src.presentation.dependency.auth import GUARD_ATTRIBUTE
from src.presentation.dependency.usecase import get_user_authorities
from src.presentation.endpoint import auth as auth_endpoint
from src.presentation.exception import install_exception_handlers
from src.presentation.middleware import install_context_middleware
from src.presentation.security import bearer_token

ORG, OTHER_ORG, TENANT = "org-1", "org-2", "tenant-1"


def principal(*permissions: str, roles: tuple[str, ...] = ()) -> Principal:
    return Principal("u1", ORG, TENANT, frozenset(roles), frozenset(permissions))


# ---------------------------------------------------------------- principal
def test_permission_wildcards_and_roles():
    assert principal("role:add").has_permission("role:add")
    assert not principal("role:add").has_permission("role:delete")
    assert principal("role:*").has_permission("role:delete")
    assert not principal("role:*").has_permission("user:add")
    assert principal("*").has_permission("anything:at-all")
    assert principal("role:add").has_permission("user:add", "role:add")  # any of
    assert principal(roles=("admin",)).has_role("auditor", "admin")
    assert not principal(roles=("admin",)).has_role("auditor")
    assert principal("*").has_role("whatever")


def test_bearer_token_parsing():
    assert bearer_token("Bearer abc") == "abc"
    assert bearer_token("bearer abc") == "abc"
    assert bearer_token("Basic abc") is None
    assert bearer_token("Bearer ") is None
    assert bearer_token(None) is None


# ---------------------------------------------------------------- session + authority cache
async def test_session_lifecycle(cache: InMemoryCache):
    auth = AuthService(cache)
    token = await auth.issue(Session("u1", ORG, TENANT))
    assert (await auth.resolve(token)).value == Session("u1", ORG, TENANT)
    assert (await auth.resolve("forged")).is_none()
    await auth.revoke(token)
    assert (await auth.resolve(token)).is_none()


async def test_cached_authorities_are_evicted_per_organization(cache: InMemoryCache):
    auth = AuthService(cache)
    granted = GrantedAuthorities(("admin",), ("role:*",))
    await auth.cache_authorities(ORG, "u1", granted)
    await auth.cache_authorities(OTHER_ORG, "u1", granted)
    assert (await auth.cached_authorities(ORG, "u1")).value == granted

    await auth.invalidate_authorities(ORG)

    assert (await auth.cached_authorities(ORG, "u1")).is_none()
    assert (await auth.cached_authorities(OTHER_ORG, "u1")).value == granted


async def test_principal_is_computed_once_then_cached(cache: InMemoryCache):
    calls: list[str] = []

    async def authorities(org: str, user: str, project: str | None):
        calls.append(user)
        return Ok(AuthorityModel(user_uuid=user, role_codes=["admin"], permission_codes=["role:*"], menus=[]))

    auth = AuthService(cache)
    session = Session("u1", ORG, TENANT)
    first = await auth_uc.load_principal(auth, authorities, session)
    second = await auth_uc.load_principal(auth, authorities, session)

    assert first == second == Ok(Principal.of(session, GrantedAuthorities(("admin",), ("role:*",))))
    assert calls == ["u1"]


# ---------------------------------------------------------------- login
class _Hasher:
    def hash(self, raw: str) -> str:
        return f"h:{raw}"

    def verify(self, raw: str, hashed: str) -> bool:
        return hashed == f"h:{raw}"


def _user(*, enabled: bool = True) -> Any:
    return SimpleNamespace(user_uuid="u1", enabled=enabled, password_hash=SimpleNamespace(value="h:Secret123"))


class _Users:
    def __init__(self, user: Any | None) -> None:
        self._user = user

    async def find_by_username(self, org: str, tenant: str, username: str):
        return Some(self._user) if self._user else option.NOTHING


class _Tenants:
    def __init__(self, *, active: bool = True) -> None:
        self._active = active

    async def get(self, org: str, tenant: str):
        tenant_ = SimpleNamespace(ensure_active=lambda now: Ok(None) if self._active else Error("inactive"))
        return Ok(tenant_)


def _login(cache: InMemoryCache, user: Any | None, *, active: bool = True):
    auth = AuthService(cache)
    return auth, auth_uc.login(cast(Any, _Users(user)), cast(Any, _Tenants(active=active)), _Hasher(), auth)


async def test_login_issues_a_token_for_valid_credentials(cache: InMemoryCache):
    auth, login = _login(cache, _user())
    result = await login(LoginCommand(ORG, TENANT, "alice", "Secret123"))
    assert isinstance(result, Ok)
    assert (await auth.resolve(result.ok.access_token)).value == Session("u1", ORG, TENANT)


@pytest.mark.parametrize(
    ("user", "password", "code"),
    [
        (None, "Secret123", "invalid_credentials"),  # unknown user answers like a wrong password
        (_user(), "Wrong-password1", "invalid_credentials"),
        (_user(enabled=False), "Secret123", "user_disabled"),
    ],
)
async def test_login_rejects_bad_credentials(cache: InMemoryCache, user, password, code):
    _, login = _login(cache, user)
    result = await login(LoginCommand(ORG, TENANT, "alice", password))
    assert isinstance(result, Error)
    assert result.error.code == code


async def test_login_rejects_an_inactive_tenant(cache: InMemoryCache):
    _, login = _login(cache, _user(), active=False)
    assert isinstance(await login(LoginCommand(ORG, TENANT, "alice", "Secret123")), Error)


# ---------------------------------------------------------------- guards over HTTP
def _guarded_app(*, enabled: bool = True, platform_org: str | None = None) -> tuple[TestClient, str]:
    settings = Settings(
        app=AppConfig(broker="memory", cache="memory"), auth=AuthConfig(enabled=enabled, platform_org_uuid=platform_org)
    )
    resources = build_resources(settings)

    async def authorities(org: str, user: str, project: str | None):
        return Ok(AuthorityModel(user_uuid=user, role_codes=["auditor"], permission_codes=["role:list"], menus=[]))

    router = APIRouter()

    @router.post("/needs-role-add", dependencies=[has_permission("role:add")])
    async def needs_role_add() -> dict[str, str]:
        return {"ok": "yes"}

    @router.post("/needs-role-list", dependencies=[has_permission("role:list")])
    async def needs_role_list() -> dict[str, str]:
        return {"ok": "yes"}

    @router.post("/needs-admin", dependencies=[has_role("admin")])
    async def needs_admin() -> dict[str, str]:
        return {"ok": "yes"}

    @router.post("/any-user", dependencies=[authenticated()])
    async def any_user(who: PrincipalDep) -> dict[str, str]:
        return {"user": who.user_uuid}

    app = FastAPI()
    install_context_middleware(app)
    install_exception_handlers(app)
    app.include_router(router)
    app.include_router(auth_endpoint.router)
    app.state.resources = resources
    app.dependency_overrides[get_user_authorities] = lambda: authorities
    token = asyncio.run(AuthService(resources.cache, 60, 60).issue(Session("u1", ORG, TENANT)))
    return TestClient(app), token


def _call(client: TestClient, path: str, token: str | None = None, org: str = ORG):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return client.post(path, json={"requestId": "r1", "reqInfo": {"orgUuid": org}}, headers=headers).json()


def test_missing_or_unknown_token_is_401():
    client, _ = _guarded_app()
    for token in (None, "forged"):
        body = _call(client, "/needs-role-list", token)
        assert (body["code"], body["errorCode"]) == (401, "unauthenticated")


def test_permission_is_checked():
    client, token = _guarded_app()
    assert _call(client, "/needs-role-list", token) == {"ok": "yes"}
    denied = _call(client, "/needs-role-add", token)
    assert (denied["code"], denied["errorCode"]) == (403, "permission_denied")


def test_role_is_checked():
    client, token = _guarded_app()
    denied = _call(client, "/needs-admin", token)
    assert (denied["code"], denied["errorCode"]) == (403, "role_denied")


def test_operator_is_the_logged_in_user_not_a_header():
    client, token = _guarded_app()
    response = client.post(
        "/any-user",
        json={"requestId": "r1", "reqInfo": {"orgUuid": ORG}},
        headers={"Authorization": f"Bearer {token}", "X-Operator": "mallory"},
    )
    assert response.json() == {"user": "u1"}


def test_acting_on_another_organization_is_forbidden():
    client, token = _guarded_app()
    body = _call(client, "/needs-role-list", token, org=OTHER_ORG)
    assert (body["code"], body["errorCode"]) == (403, "org_mismatch")


def test_platform_organization_may_act_on_any_organization():
    client, token = _guarded_app(platform_org=ORG)
    assert _call(client, "/needs-role-list", token, org=OTHER_ORG) == {"ok": "yes"}


def test_guards_pass_when_authentication_is_off():
    client, _ = _guarded_app(enabled=False)
    assert _call(client, "/needs-role-add") == {"ok": "yes"}
    assert _call(client, "/needs-admin") == {"ok": "yes"}


# ---------------------------------------------------------------- every route is guarded
PUBLIC = {"/auth/login", "/auth/captcha", "/user/register"}  # register is protected by the captcha instead


def _guarded(route: APIRoute) -> bool:
    pending = list(route.dependant.dependencies)
    while pending:
        dep = pending.pop()
        if getattr(dep.call, GUARD_ATTRIBUTE, False):
            return True
        pending.extend(dep.dependencies)
    return False


def _routes() -> list[APIRoute]:
    """Routes of every endpoint module (the app's ``include_router`` wraps them, so read the modules)."""
    found: list[APIRoute] = []
    for info in pkgutil.iter_modules(endpoint.__path__):
        router = getattr(importlib.import_module(f"{endpoint.__name__}.{info.name}"), "router", None)
        if isinstance(router, APIRouter) and info.name != "health":
            found += [r for r in router.routes if isinstance(r, APIRoute)]
    return found


def test_every_route_is_guarded_or_explicitly_open():
    open_routes = [f"{r.path} ({r.tags})" for r in _routes() if not _guarded(r) and r.path not in PUBLIC]
    assert open_routes == [], "add has_permission(...) or authenticated() to these routes"


def test_me_returns_roles_permissions_and_the_menu_tree():
    client, token = _guarded_app()
    body = client.post(
        "/auth/me", json={"requestId": "r1", "reqInfo": {}}, headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert body["code"] == 0
    assert body["resultInfo"] == {
        "userUuid": "u1",
        "orgUuid": ORG,
        "tenantUuid": TENANT,
        "roleCodes": ["auditor"],
        "permissionCodes": ["role:list"],
        "menus": [],
    }
