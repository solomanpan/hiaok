"""Request / response envelope shared by every API.

    POST /v1/api/hiaok/<resource>/<action>
    {"requestId": "202612231234567", "reqInfo": {...}}
    -> {"code": 0, "msg": "success", "resultInfo": {...}}

``code`` 0 = success; anything else is an error and ``resultInfo`` is ``null``. ``errorCode`` (only present
on errors) is the fine-grained business code, e.g. ``system_role``.
"""

from __future__ import annotations

from collections.abc import Callable

from expression import Error, Result
from hiaok_core.exception import DomainError
from pydantic import Field

from .common import ApiModel

SUCCESS = 0
# error ``code`` per DomainError.kind (HTTP-like numbers, but the HTTP status itself stays 200)
CODE_OF_KIND = {"validation": 400, "forbidden": 403, "not_found": 404, "conflict": 409}
INVALID_REQUEST = 400
INTERNAL_ERROR = 500
UPSTREAM_ERROR = 502


class ApiRequest[T](ApiModel):
    request_id: str = Field(..., min_length=1, max_length=64, examples=["202612231234567"])
    req_info: T


class ApiResponse[T](ApiModel):
    code: int = SUCCESS
    msg: str = "success"
    result_info: T | None = None
    error_code: str | None = Field(
        default=None,
        exclude_if=lambda v: v is None,
        description="business error code; only present when code != 0",
    )

    @classmethod
    def ok(cls, result_info: T | None = None) -> ApiResponse[T]:
        return cls(result_info=result_info)

    @classmethod
    def fail(cls, code: int, msg: str, error_code: str | None = None) -> ApiResponse[T]:
        return cls(code=code, msg=msg, error_code=error_code)


def reply[T, R](result: Result[T, DomainError], to_response: Callable[[T], R]) -> ApiResponse[R]:
    """``Result`` -> envelope. Domain errors are *values*: they become ``code != 0``, not exceptions."""
    if isinstance(result, Error):
        err = result.error
        return ApiResponse[R].fail(CODE_OF_KIND[err.kind], err.message, err.code)
    return ApiResponse[R].ok(to_response(result.ok))


def done[T](result: Result[T, DomainError]) -> ApiResponse[None]:
    """For commands without a payload (delete, change password)."""
    return reply(result, lambda _: None)
