from __future__ import annotations

from datetime import datetime

from pydantic import Field

from ...application.model import CreateTenant, TenantModel, UpdateTenant
from .common import EntityResponse, MetaRequest, MetaUpdateRequest


class TenantCreateRequest(MetaRequest):
    tenant_code: str = Field(..., examples=["default"])
    tenant_name: str
    expire_time: datetime | None = None

    def to_command(self, org_uuid: str) -> CreateTenant:
        return CreateTenant(org_uuid=org_uuid, **self.model_dump())


class TenantUpdateRequest(MetaUpdateRequest):
    tenant_name: str | None = None
    expire_time: datetime | None = None

    def to_command(self) -> UpdateTenant:
        return UpdateTenant(**self.model_dump())


class TenantResponse(EntityResponse):
    tenant_uuid: str
    tenant_code: str
    tenant_name: str
    expire_time: datetime | None = None

    @classmethod
    def of(cls, m: TenantModel) -> TenantResponse:
        return cls.model_validate(m)
