"""Errors -> the response envelope.

Domain errors are values and are turned into ``code != 0`` by ``schema.envelope.reply`` inside the endpoint;
this module covers what is *raised*:

* ``DomainException``                  -> HTTP 200, ``code`` by kind (expected business outcome)
* request body that fails validation   -> HTTP 200, ``code`` 400
* ``Unauthenticated``                  -> HTTP 200, ``code`` 401 (missing / unknown / expired token)
* ``HttpClientError``                  -> HTTP 502, ``code`` 502 (a dependency is down)
* ``DataSourceRoutingError`` / ``HiaokError`` / anything else
                                       -> HTTP 500, ``code`` 500 (details are logged, not returned)
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from hiaok_core.exception import DomainException, HiaokError, HttpClientError

from ..infrastructure.database import DataSourceRoutingError, NoActiveScopeError
from .i18n import localize, static_message
from .schema.envelope import (
    CODE_OF_KIND,
    INTERNAL_ERROR,
    INVALID_REQUEST,
    UNAUTHENTICATED,
    UPSTREAM_ERROR,
    ApiResponse,
)
from .security import Unauthenticated

log = logging.getLogger(__name__)


def _json(code: int, msg: str, error_code: str | None, status: int = 200) -> JSONResponse:
    body = ApiResponse[None].fail(code, msg, error_code).model_dump(by_alias=True)
    return JSONResponse(body, status_code=status)


def _first_problem(exc: RequestValidationError) -> str:
    err = exc.errors()[0]
    where = ".".join(str(p) for p in err["loc"] if p != "body")
    return f"{where}: {err['msg']}" if where else str(err["msg"])


def install_exception_handlers(app: FastAPI) -> None:
    async def domain_exception(_: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, DomainException)
        return _json(CODE_OF_KIND[exc.error.kind], localize(exc.error), exc.error.code)

    async def invalid_request(_: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, RequestValidationError)
        return _json(INVALID_REQUEST, _first_problem(exc), "invalid_request")

    async def unauthenticated(_: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, Unauthenticated)
        return _json(UNAUTHENTICATED, static_message(exc.message), exc.code)

    async def upstream_error(_: Request, exc: Exception) -> JSONResponse:
        log.warning("upstream call failed: %s", exc)
        return _json(UPSTREAM_ERROR, str(exc), getattr(exc, "code", "http_client_error"), status=502)

    async def routing_error(_: Request, exc: Exception) -> JSONResponse:
        log.exception("datasource routing failed", exc_info=exc)
        return _json(INTERNAL_ERROR, static_message("internal error"), "datasource_routing", status=500)

    async def hiaok_error(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled %s", type(exc).__name__, exc_info=exc)
        return _json(
            INTERNAL_ERROR, static_message("internal error"), getattr(exc, "code", "internal_error"), status=500
        )

    app.add_exception_handler(DomainException, domain_exception)
    app.add_exception_handler(RequestValidationError, invalid_request)
    app.add_exception_handler(Unauthenticated, unauthenticated)
    app.add_exception_handler(HttpClientError, upstream_error)
    app.add_exception_handler(DataSourceRoutingError, routing_error)
    app.add_exception_handler(NoActiveScopeError, routing_error)
    app.add_exception_handler(HiaokError, hiaok_error)
    app.add_exception_handler(Exception, hiaok_error)
