"""One-time captcha for login / register: the service, the image, and the guarded endpoints."""

from __future__ import annotations

import base64
import random
import re

from expression import Error, Ok
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.application.config import AppConfig, AuthConfig, Settings
from src.application.service import CaptchaService
from src.application.service.captcha_service import ALPHABET, CODE_LENGTH
from src.infrastructure.cache.memory_cache import InMemoryCache
from src.infrastructure.resources import build_resources
from src.presentation.captcha import data_uri, render_svg
from src.presentation.dependency.auth import CaptchaGuard
from src.presentation.endpoint import auth as auth_endpoint
from src.presentation.exception import install_exception_handlers
from src.presentation.middleware import install_context_middleware


# ---------------------------------------------------------------- service
async def test_a_captcha_can_be_solved_once(cache: InMemoryCache):
    service = CaptchaService(cache, 60)
    captcha_id, code = await service.issue()
    assert len(code) == CODE_LENGTH and set(code) <= set(ALPHABET)
    assert await service.verify(captcha_id, code.lower())  # case-insensitive
    assert not await service.verify(captcha_id, code)  # consumed by the first check


async def test_a_wrong_answer_burns_the_captcha(cache: InMemoryCache):
    service = CaptchaService(cache, 60)
    captcha_id, code = await service.issue()
    assert not await service.verify(captcha_id, "ZZZZ" if code != "ZZZZ" else "YYYY")
    assert not await service.verify(captcha_id, code)  # no brute force against one id


async def test_missing_unknown_or_blank_answers_fail(cache: InMemoryCache):
    service = CaptchaService(cache, 60)
    captcha_id, _ = await service.issue()
    assert not await service.verify(None, "ABCD")
    assert not await service.verify(captcha_id, None)
    assert not await service.verify(captcha_id, "")
    assert not await service.verify("forged", "ABCD")


# ---------------------------------------------------------------- image
def test_the_image_is_an_svg_data_uri():
    svg = render_svg("A2B3", random.Random(1))
    assert svg.startswith("<svg") and svg.endswith("</svg>")
    assert all(ch in svg for ch in "A2B3")
    uri = data_uri(svg)
    assert uri.startswith("data:image/svg+xml;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]).decode() == svg


# ---------------------------------------------------------------- endpoints
def _client(enabled: bool) -> TestClient:
    settings = Settings(
        app=AppConfig(broker="memory", cache="memory"), auth=AuthConfig(enabled=False, captcha_enabled=enabled)
    )
    app = FastAPI()
    install_context_middleware(app)
    install_exception_handlers(app)
    app.include_router(auth_endpoint.router)
    app.state.resources = build_resources(settings)
    return TestClient(app)


def _post(client: TestClient, path: str, info: dict | None = None):
    return client.post(path, json={"requestId": "r1", "reqInfo": info or {}}).json()


def test_captcha_endpoint_reports_that_it_is_off():
    body = _post(_client(False), "/auth/captcha")
    assert body["code"] == 0 and body["resultInfo"] == {
        "required": False,
        "captchaId": None,
        "image": None,
        "expiresIn": None,
    }


def test_login_demands_a_solved_captcha_when_enabled():
    client = _client(True)
    login = {"orgUuid": "o", "tenantUuid": "t", "username": "alice", "password": "secret-password"}

    missing = _post(client, "/auth/login", login)
    assert (missing["code"], missing["errorCode"]) == (400, "captcha_invalid")

    issued = _post(client, "/auth/captcha")["resultInfo"]
    assert issued["required"] is True and issued["expiresIn"] == 120
    assert re.fullmatch(r"data:image/svg\+xml;base64,[A-Za-z0-9+/=]+", issued["image"])

    wrong = _post(client, "/auth/login", {**login, "captchaId": issued["captchaId"], "captchaCode": "!!!!"})
    assert wrong["errorCode"] == "captcha_invalid"
    assert (
        _post(client, "/auth/login", {**login, "captchaId": issued["captchaId"], "captchaCode": "!!!!"})["errorCode"]
        == "captcha_invalid"
    )


def test_captcha_error_is_translated():
    client = _client(True)
    res = client.post(
        "/auth/login",
        json={"requestId": "r1", "reqInfo": {"orgUuid": "o", "tenantUuid": "t", "username": "a", "password": "b"}},
        headers={"Accept-Language": "zh"},
    ).json()
    assert res["msg"] == "验证码缺失、已过期或错误"


async def test_the_guard_passes_a_solved_captcha_and_is_a_no_op_when_off(cache: InMemoryCache):
    service = CaptchaService(cache, 60)
    captcha_id, code = await service.issue()
    guard = CaptchaGuard(service, True)
    assert isinstance(await guard(captcha_id, code), Ok)
    assert isinstance(await guard(captcha_id, code), Error)  # one-time
    assert isinstance(await CaptchaGuard(service, False)(None, None), Ok)


# ---------------------------------------------------------------- CORS for the web / desktop / mobile console
def test_cors_is_off_by_default_and_follows_APP_CORS_ORIGINS():
    from src.main import create_app

    def preflight(origins: str):
        settings = Settings(app=AppConfig(broker="memory", cache="memory", consume_events=False, cors_origins=origins))
        client = TestClient(create_app(settings))
        return client.options(
            "/v1/api/hiaok/auth/login",
            headers={
                "Origin": "tauri://localhost",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    assert "access-control-allow-origin" not in preflight("").headers
    allowed = preflight("http://localhost:5173, tauri://localhost")
    assert allowed.headers["access-control-allow-origin"] == "tauri://localhost"
    assert "authorization" in allowed.headers["access-control-allow-headers"].lower()
