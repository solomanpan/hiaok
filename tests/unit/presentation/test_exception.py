from typing import cast

import pytest
from expression import Error, Ok
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from hiaok_core.exception import (
    DomainException,
    HiaokError,
    HttpClientError,
    conflict,
    forbidden,
    not_found,
    validation,
)

from src.presentation.exception import install_exception_handlers, unwrap


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (validation("bad", "m"), 422),
        (not_found("Role", "r1"), 404),
        (conflict("dup", "m"), 409),
        (forbidden("no", "m"), 403),
    ],
)
def test_unwrap_maps_error_kind_to_status(error, status):
    with pytest.raises(HTTPException) as exc:
        unwrap(Error(error), lambda x: x)
    assert exc.value.status_code == status
    assert cast(dict[str, str], exc.value.detail)["code"] == error.code


def test_unwrap_ok_maps_value():
    assert unwrap(Ok(2), lambda x: x * 10) == 20


def test_routing_error_becomes_500():
    from src.infrastructure.database import NoActiveScopeError

    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise NoActiveScopeError("no scope")

    r = TestClient(app).get("/boom")
    assert r.status_code == 500 and r.json()["detail"]["code"] == "datasource_routing"


def _app_raising(exc: Exception):
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise exc

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("exc", "status", "code"),
    [
        (DomainException(conflict("dup", "duplicate")), 409, "dup"),
        (HttpClientError("upstream down", status=503), 502, "http_client_error"),
        (HiaokError("secret details"), 500, "internal_error"),
    ],
)
def test_raised_hiaok_errors_map_to_http(exc, status, code):
    r = _app_raising(exc).get("/boom")
    assert r.status_code == status
    assert r.json()["detail"]["code"] == code
    if status == 500:
        assert "secret" not in r.text  # internal messages are not leaked
