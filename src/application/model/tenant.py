from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import Tenant
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class TenantModel(EntityModel):
    tenant_uuid: str
    tenant_code: str
    tenant_name: str
    expire_time: datetime | None = None

    @classmethod
    def from_domain(cls, t: Tenant) -> TenantModel:
        return cls(
            **entity_fields(t),
            tenant_uuid=t.tenant_uuid,
            tenant_code=t.tenant_code.value,
            tenant_name=t.tenant_name,
            expire_time=t.expire_time,
        )

    def to_domain(self) -> Tenant:
        return Tenant(
            **entity_kwargs(self),
            tenant_uuid=self.tenant_uuid,
            tenant_code=Code(self.tenant_code),
            tenant_name=self.tenant_name,
            expire_time=self.expire_time,
        )


@dataclass(frozen=True, kw_only=True)
class CreateTenant(CreateMeta):
    org_uuid: str
    tenant_code: str
    tenant_name: str
    expire_time: datetime | None = None

    def to_domain(self, uuid: str) -> Result[Tenant, DomainError]:
        return Tenant.create(
            self.org_uuid,
            uuid,
            self.tenant_code,
            self.tenant_name,
            expire_time=self.expire_time,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateTenant(UpdateMeta):
    tenant_name: str | None = None
    expire_time: datetime | None = None

    def apply_to(self, t: Tenant) -> Result[Tenant, DomainError]:
        return t.update(tenant_name=self.tenant_name, expire_time=self.expire_time).map(self.apply_meta)
