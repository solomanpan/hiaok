"""Raised errors -> the response envelope (domain *values* are covered in test_envelope)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hiaok_core.exception import DomainException, HiaokError, HttpClientError, conflict

from src.infrastructure.database import NoActiveScopeError
from src.presentation.exception import install_exception_handlers


def _client(exc: Exception) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise exc

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("exc", "http_status", "code", "error_code"),
    [
        (DomainException(conflict("dup", "duplicate")), 200, 409, "dup"),
        (HttpClientError("upstream down", status=503), 502, 502, "http_client_error"),
        (HiaokError("secret details"), 500, 500, "internal_error"),
        (NoActiveScopeError("no scope"), 500, 500, "datasource_routing"),
        (RuntimeError("secret details"), 500, 500, "internal_error"),
    ],
)
def test_raised_errors_become_envelopes(exc, http_status, code, error_code):
    r = _client(exc).get("/boom")
    assert r.status_code == http_status
    body = r.json()
    assert body["code"] == code
    assert body["errorCode"] == error_code
    assert body["resultInfo"] is None
    if http_status == 500:
        assert "secret" not in r.text  # internal messages are not leaked
