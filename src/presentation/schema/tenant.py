from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ...application.model import CreateTenant, TenantModel, UpdateTenant
from .common import EntityResponse, Keyed, MetaRequest, MetaUpdateRequest, OrgScoped


class TenantCreateRequest(OrgScoped, MetaRequest):
    tenant_code: str = Field(..., examples=["default"])
    tenant_name: str
    expire_time: datetime | None = None

    def to_command(self) -> CreateTenant:
        return CreateTenant(**self.model_dump())


class TenantUpdateRequest(Keyed, MetaUpdateRequest):
    tenant_name: str | None = None
    expire_time: datetime | None = None

    def to_command(self) -> UpdateTenant:
        return UpdateTenant(**self.patch())


class TenantResponse(EntityResponse):
    tenant_uuid: str
    tenant_code: str
    tenant_name: str
    expire_time: datetime | None = None

    @classmethod
    def of(cls, m: TenantModel) -> TenantResponse:
        return cls.model_validate(m)
