"""Routers: ``POST /v1/api/hiaok/<resource>/<action>``.

Each endpoint: ``ApiRequest[request DTO]`` -> usecase (injected) -> ``ApiResponse[response DTO]``.
"""

from fastapi import APIRouter, Depends

from ..openapi import context_headers
from . import (
    auth,
    department,
    employee,
    health,
    menu,
    organization,
    permission,
    project,
    role,
    sys_config,
    sys_log,
    tenant,
    user,
    user_group,
)

API_PREFIX = "/v1/api/hiaok"
api_router = APIRouter(prefix=API_PREFIX, dependencies=[Depends(context_headers)])
for module in (
    auth,
    organization,
    tenant,
    user,
    user_group,
    project,
    role,
    permission,
    menu,
    department,
    employee,
    sys_config,
    sys_log,
):
    api_router.include_router(module.router)

__all__ = ["api_router", "health"]
