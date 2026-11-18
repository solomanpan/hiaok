from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from expression import Error, Ok, Result, effect
from hiaok_core.exception import DomainError, validation

from ..vo import Code, non_blank
from .base import AggregateRoot


@dataclass(frozen=True, kw_only=True)
class Tenant(AggregateRoot):
    tenant_uuid: str
    tenant_code: Code
    tenant_name: str
    expire_time: datetime | None = None

    @property
    def uuid(self) -> str:
        return self.tenant_uuid

    @staticmethod
    def create(
        org_uuid: str,
        tenant_uuid: str,
        tenant_code: str,
        tenant_name: str,
        *,
        expire_time: datetime | None = None,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Tenant, DomainError]:
        @effect.result[Tenant, DomainError]()
        def build() -> Generator[Any, Any, Tenant]:
            code = yield from Code.create(tenant_code, "tenant_code")
            name = yield from non_blank(tenant_name, "tenant_name")
            tenant = Tenant(
                org_uuid=org_uuid,
                tenant_uuid=tenant_uuid,
                tenant_code=code,
                tenant_name=name,
                expire_time=expire_time,
                description=description,
                remark=remark,
            )
            return tenant.created()

        return build()

    def update(
        self, *, tenant_name: str | None = None, expire_time: datetime | None = None
    ) -> Result[Tenant, DomainError]:
        @effect.result[Tenant, DomainError]()
        def build() -> Generator[Any, Any, Tenant]:
            name = (yield from non_blank(tenant_name, "tenant_name")) if tenant_name is not None else self.tenant_name
            return self.changed(tenant_name=name, expire_time=expire_time or self.expire_time)

        return build()

    def is_expired(self, now: datetime) -> bool:
        return self.expire_time is not None and self.expire_time <= now

    def ensure_active(self, now: datetime) -> Result[Tenant, DomainError]:
        if not self.enabled or self.is_expired(now):
            return Error(validation("tenant_inactive", f"tenant '{self.tenant_uuid}' is disabled or expired"))
        return Ok(self)
