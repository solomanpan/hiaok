from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from hiaok_core.context import request_context

from ..infrastructure.resources import Resources
from .i18n import parse_accept_language, set_locale
from .security import auth_service, bearer_token

ANONYMOUS = "anonymous"


async def _identity(request: Request) -> dict[str, str | None]:
    """Who is calling: from the login token when authentication is on, else from ``X-Operator``."""
    resources: Resources | None = getattr(request.app.state, "resources", None)
    if resources is None:
        return {"operator": request.headers.get("x-operator", ANONYMOUS)}
    if not resources.settings.auth.enabled:
        return {"operator": request.headers.get("x-operator", ANONYMOUS)}
    token = bearer_token(request.headers.get("authorization"))
    session = await auth_service(resources).resolve(token) if token else None
    if session is None or session.is_none():
        return {"operator": ANONYMOUS}
    s = session.value
    return {"operator": s.user_uuid, "user_uuid": s.user_uuid, "org_uuid": s.org_uuid, "tenant_uuid": s.tenant_uuid}


def install_context_middleware(app: FastAPI) -> None:
    """Fills the request context: operator (written to ``opr``), user / org / tenant and the trace id.

    ``Accept-Language`` picks the language of error messages (``en`` / ``zh`` / ``ja``, echoed as ``Content-Language``).
    ``X-Request-Id`` is the trace id (echoed back). The principal's roles are checked later, per endpoint, by the
    ``has_permission`` / ``has_role`` dependencies.
    """

    @app.middleware("http")
    async def context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        identity = await _identity(request)
        resources: Resources | None = getattr(request.app.state, "resources", None)
        locale = parse_accept_language(
            request.headers.get("accept-language"), resources.settings.app.default_locale if resources else "en"
        )
        set_locale(locale)
        with request_context(trace_id=request.headers.get("x-request-id"), **identity) as ctx:  # type: ignore[arg-type]
            response = await call_next(request)
        response.headers["x-request-id"] = ctx.trace_id
        response.headers["content-language"] = locale
        return response
