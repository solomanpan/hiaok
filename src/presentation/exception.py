"""Errors -> HTTP. The only place that knows about status codes.

* ``unwrap(result, to_response)``  - ``Result.Error(DomainError)`` -> ``HTTPException`` (the normal path)
* exception handlers               - raised ``hiaok_core.exception.HiaokError`` subclasses
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from expression import Error, Result
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from hiaok_core.exception import DomainError, DomainException, HiaokError, HttpClientError

from ..infrastructure.database import DataSourceRoutingError, NoActiveScopeError

log = logging.getLogger(__name__)

STATUS = {"validation": 422, "not_found": 404, "conflict": 409, "forbidden": 403}


def _body(code: str, message: str) -> dict[str, dict[str, str]]:
    return {"detail": {"code": code, "message": message}}


def unwrap[T, R](result: Result[T, DomainError], to_response: Callable[[T], R]) -> R:
    if isinstance(result, Error):
        err = result.error
        raise HTTPException(STATUS[err.kind], detail={"code": err.code, "message": err.message})
    return to_response(result.ok)


def install_exception_handlers(app: FastAPI) -> None:
    async def domain_exception(_: Request, exc: Exception) -> JSONResponse:
        assert isinstance(exc, DomainException)
        return JSONResponse(_body(exc.error.code, exc.error.message), status_code=STATUS[exc.error.kind])

    async def upstream_error(_: Request, exc: Exception) -> JSONResponse:
        log.warning("upstream call failed: %s", exc)
        return JSONResponse(_body(getattr(exc, "code", "http_client_error"), str(exc)), status_code=502)

    async def routing_error(_: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(_body("datasource_routing", str(exc)), status_code=500)

    async def hiaok_error(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled %s", type(exc).__name__, exc_info=exc)
        return JSONResponse(_body(getattr(exc, "code", "internal_error"), "internal error"), status_code=500)

    app.add_exception_handler(DomainException, domain_exception)
    app.add_exception_handler(HttpClientError, upstream_error)
    app.add_exception_handler(DataSourceRoutingError, routing_error)
    app.add_exception_handler(NoActiveScopeError, routing_error)
    app.add_exception_handler(HiaokError, hiaok_error)
