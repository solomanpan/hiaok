"""Routers. Each endpoint: request DTO -> use case (injected) -> response DTO."""

from fastapi import APIRouter, Depends

from ..openapi import ERROR_RESPONSES, context_headers
from . import (
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

api_router = APIRouter(prefix="/api/v1", responses=ERROR_RESPONSES, dependencies=[Depends(context_headers)])
for module in (
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
