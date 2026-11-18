from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from hiaok_core.context import request_context


def install_context_middleware(app: FastAPI) -> None:
    """``X-Operator`` (who acts, written to ``opr``) and ``X-Request-Id`` (trace id, echoed back).

    Replace the header with the authenticated principal once authentication is in place.
    """

    @app.middleware("http")
    async def context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        operator = request.headers.get("x-operator", "anonymous")
        with request_context(operator=operator, trace_id=request.headers.get("x-request-id")) as ctx:
            response = await call_next(request)
        response.headers["x-request-id"] = ctx.trace_id
        return response
