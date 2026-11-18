"""OpenAPI / Swagger UI configuration (``/docs`` Swagger UI, ``/redoc`` ReDoc, ``/openapi.json``).

Everything here is documentation only: no runtime behaviour depends on it.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Annotated, Any

from fastapi import Header
from fastapi.routing import APIRoute

try:
    API_VERSION = version("hiaok")
except PackageNotFoundError:  # running from a source tree that is not installed
    API_VERSION = "0.0.0"

DESCRIPTION = """
轻量级权限中心（DDD · 事件驱动 · 读写分离）。

### 接口规范
所有业务接口均为 `POST /v1/api/hiaok/<资源>/<动作>`（动作：`add` / `list` / `get` / `update` / `delete` 及各资源的专有动作）。

请求体统一为 `{"requestId": "...", "reqInfo": {...}}`，
响应体统一为 `{"code": 0, "msg": "success", "resultInfo": {...}}`；字段名一律 camelCase。资源所属组织与目标资源分别用 `reqInfo.orgUuid`、`reqInfo.uuid` 传递。

### 异步写入
`add` / `update` / `delete` 和专有写动作（授权、移动、调动、离职…）只负责受理：校验请求格式后发到 Kafka，立即返回
`{"code": 0, "resultInfo": {"requestId": "...", "uuid": "...", "status": "accepted"}}`，由消费者异步入库。
业务规则（重复编码、资源不存在…）在消费时才判断，结果用 `/log/get-by-request` 按 `requestId` 查询
（`success` / `failed` / `pending`）。新增时返回的 `uuid` 就是新实体的 uuid。
用户注册、修改密码、员工入职（带明文密码）仍是同步接口，直接返回结果。

### 请求头
| Header | 说明 |
|---|---|
| `Authorization` | `Bearer <token>`（`POST /auth/login` 获取；受保护接口必填，缺失或失效返回 `code` 401） |
| `X-Operator` | 操作人，写入审计字段 `opr`；仅在 `AUTH_ENABLED=false` 时使用，开启认证后操作人就是登录用户 |
| `X-Request-Id` | 链路追踪 id，原样回显在响应头；缺省自动生成 |

### 错误
可预期的错误一律 HTTP 200，通过 `code` / `msg` 表达，`resultInfo` 为 `null`，
并附带细分的 `errorCode`（如 `role_not_found`）：

| code | 含义 |
|---|---|
| 0 | 成功 |
| 400 | validation — 业务校验失败，或请求体格式错误（`errorCode` = `invalid_request`） |
| 401 | unauthenticated — 未登录或 token 失效（`errorCode` = `unauthenticated` / `invalid_credentials`） |
| 403 | forbidden — 无权限（`permission_denied` / `role_denied`），或操作了不属于自己的组织（`org_mismatch`） |
| 404 | not_found — 资源不存在 |
| 409 | conflict — 状态冲突（如重复编码、删除系统角色） |
| 502 | 依赖的上游服务调用失败（HTTP 502） |
| 500 | 未预期的系统错误（HTTP 500，细节只写日志） |

### 分页
列表接口在 `reqInfo` 里传 `offset`（默认 0）/ `limit`（默认 20，最大 200），
`resultInfo` 为 `items / total / offset / limit`。
"""

OPENAPI_TAGS: list[dict[str, Any]] = [
    {"name": "health", "description": "健康检查：主从数据源连通性"},
    {"name": "auth", "description": "登录、登出、当前身份（Bearer token）"},
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


async def context_headers(
    x_operator: Annotated[
        str | None, Header(description="操作人（写入 opr）；仅在 AUTH_ENABLED=false 时生效，缺省 anonymous")
    ] = None,
    x_request_id: Annotated[str | None, Header(description="链路追踪 id，回显在响应头")] = None,
) -> None:
    """Documents the headers read by ``install_context_middleware`` so Swagger UI can send them."""


def operation_id(route: APIRoute) -> str:
    """``role-create_role`` instead of ``create_role_api_v1_orgs__org_uuid__roles_post`` (nicer client codegen)."""
    return f"{route.tags[0]}-{route.name}" if route.tags else route.name
