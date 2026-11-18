"""Authentication plumbing shared by the middleware, the dependencies and the exception handlers."""

from __future__ import annotations

from hiaok_core.exception import HiaokError
from hiaok_core.factory import ErrorCatalog, ErrorSpec

from ..application.service import AuthService
from ..infrastructure.resources import Resources


class Unauthenticated(HiaokError):
    """No / unknown / expired token. Becomes ``code`` 401 in the envelope (HTTP status stays 200)."""

    code = "unauthenticated"

    def __init__(self, message: str = "authentication required") -> None:
        super().__init__(message)


class SecurityErrors(ErrorCatalog):
    permission_denied = ErrorSpec.forbidden("permission_denied", "requires permission {required}")
    role_denied = ErrorSpec.forbidden("role_denied", "requires role {required}")
    org_mismatch = ErrorSpec.forbidden("org_mismatch", "not allowed to act on organization '{org_uuid}'")


def bearer_token(authorization: str | None) -> str | None:
    """``Authorization: Bearer <token>`` -> ``<token>``."""
    scheme, _, token = (authorization or "").partition(" ")
    return token.strip() or None if scheme.lower() == "bearer" else None


def auth_service(resources: Resources) -> AuthService:
    cfg = resources.settings.auth
    return AuthService(resources.cache, cfg.session_ttl_seconds, cfg.authority_ttl_seconds)
