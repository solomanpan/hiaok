from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Ok, Result, effect
from hiaok_core.exception import DomainError

from ..vo import Code, non_blank
from .base import AggregateRoot
from .event import EntityUpdated
from .org_detail import OrgDetail


@dataclass(frozen=True, kw_only=True)
class Organization(AggregateRoot):
    """Root of the tenancy tree. ``org_uuid`` is both its identity and its scope."""

    org_code: Code
    org_name: str
    detail: OrgDetail

    @property
    def uuid(self) -> str:
        return self.org_uuid

    @staticmethod
    def create(
        org_uuid: str,
        org_code: str,
        org_name: str,
        *,
        detail: OrgDetail | None = None,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Organization, DomainError]:
        @effect.result[Organization, DomainError]()
        def build() -> Generator[Any, Any, Organization]:
            code = yield from Code.create(org_code, "org_code")
            name = yield from non_blank(org_name, "org_name")
            org = Organization(
                org_uuid=org_uuid,
                org_code=code,
                org_name=name,
                detail=detail or OrgDetail.empty(org_uuid),
                description=description,
                remark=remark,
            )
            return org.created()

        return build()

    def rename(self, org_name: str | None) -> Result[Organization, DomainError]:
        if org_name is None:
            return Ok(self)
        return non_blank(org_name, "org_name").map(lambda name: self.changed(org_name=name))

    def update_detail(self, detail: OrgDetail) -> Organization:
        if detail == self.detail:
            return self
        return self.changed(detail=detail).record(
            EntityUpdated(
                org_uuid=self.org_uuid, entity_type="OrgDetail", entity_uuid=self.org_uuid, changed_fields=("detail",)
            )
        )
