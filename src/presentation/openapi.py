"""OpenAPI / Swagger UI configuration (``/docs`` Swagger UI, ``/redoc`` ReDoc, ``/openapi.json``).

Everything here is documentation only: no runtime behaviour depends on it.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Annotated, Any

from fastapi import Header
from fastapi.routing import APIRoute
from pydantic import BaseModel

from .schema.common import ErrorResponse

try:
    API_VERSION = version("hiaok")
except PackageNotFoundError:  # running from a source tree that is not installed
    API_VERSION = "0.0.0"

DESCRIPTION = """
轻量级权限中心（DDD · 事件驱动 · 读写分离）。

### 请求头
| Header | 说明 |
|---|---|
| `X-Operator` | 操作人，写入审计字段 `opr`（接入认证后由登录主体替代），缺省 `anonymous` |
| `X-Request-Id` | 链路追踪 id，原样回显在响应头；缺省自动生成 |

### 错误格式
领域错误统一返回 `{"detail": {"code": "...", "message": "..."}}`：

| 状态码 | 含义 |
|---|---|
| 403 | forbidden — 无权限 |
| 404 | not_found — 资源不存在（code 形如 `role_not_found`） |
| 409 | conflict — 状态冲突（如重复编码、删除系统角色） |
| 422 | validation — 业务校验失败；请求体格式错误时为 FastAPI 标准校验结构 |

### 分页
列表接口使用 `offset`（默认 0）/ `limit`（默认 20，最大 200），返回 `items / total / offset / limit`。
"""

OPENAPI_TAGS: list[dict[str, Any]] = [
    {"name": "health", "description": "健康检查：主从数据源连通性"},
    {"name": "organization", "description": "组织：开通（组织 + 默认租户 + 管理员角色 + 默认配置）与维护"},
    {"name": "tenant", "description": "租户"},
    {"name": "user", "description": "用户：注册、角色分配、改密、查询权限"},
    {"name": "user_group", "description": "用户组（树形）"},
    {"name": "project", "description": "项目"},
    {"name": "role", "description": "角色：授予权限、分配菜单"},
    {"name": "permission", "description": "权限点（`resource:action`，支持 `resource:*` / `*`）"},
    {"name": "menu", "description": "菜单（树形）"},
    {"name": "department", "description": "部门（树形）"},
    {"name": "employee", "description": "员工：入职（可同时开通用户）"},
    {"name": "sys_config", "description": "系统配置（带缓存，变更时事件驱动失效）"},
    {"name": "sys_log", "description": "审计日志（由领域事件写入，只读）"},
]

SWAGGER_UI_PARAMETERS: dict[str, Any] = {
    "docExpansion": "none",  # 13 tags x ~6 ops: start collapsed
    "filter": True,
    "displayRequestDuration": True,
    "persistAuthorization": True,
    "tryItOutEnabled": True,
    "defaultModelsExpandDepth": 0,
}


class ErrorEnvelope(BaseModel):
    """Shape produced by ``errors.unwrap`` (``HTTPException(detail={code, message})``)."""

    detail: ErrorResponse


def _error(description: str) -> dict[str, Any]:
    return {"model": ErrorEnvelope, "description": description}


# 422 is deliberately not listed: FastAPI only documents its request-validation schema when the
# route does not declare 422 itself, and that schema is the more useful one to show.
ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    403: _error("Forbidden"),
    404: _error("Not found"),
    409: _error("Conflict"),
}


async def context_headers(
    x_operator: Annotated[str | None, Header(description="操作人（写入 opr），缺省 anonymous")] = None,
    x_request_id: Annotated[str | None, Header(description="链路追踪 id，回显在响应头")] = None,
) -> None:
    """Documents the headers read by ``install_context_middleware`` so Swagger UI can send them."""


def operation_id(route: APIRoute) -> str:
    """``role-create_role`` instead of ``create_role_api_v1_orgs__org_uuid__roles_post`` (nicer client codegen)."""
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name
