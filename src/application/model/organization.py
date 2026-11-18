from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

from expression import Result, effect
from hiaok_core.exception import DomainError

from ...domain.entity import Organization, OrgDetail
from ...domain.vo import Code, Email, PhoneNumber, text_or_none
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class OrgDetailModel:
    legal_name: str | None = None
    registration_no: str | None = None
    address: str | None = None
    postal_code: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    website: str | None = None

    @classmethod
    def from_domain(cls, d: OrgDetail) -> OrgDetailModel:
        return cls(
            legal_name=d.legal_name,
            registration_no=d.registration_no,
            address=d.address,
            postal_code=d.postal_code,
            contact_name=d.contact_name,
            contact_phone=text_or_none(d.contact_phone),
            contact_email=text_or_none(d.contact_email),
            website=d.website,
        )

    def to_domain(self, org_uuid: str) -> OrgDetail:
        return OrgDetail(
            org_uuid=org_uuid,
            legal_name=self.legal_name,
            registration_no=self.registration_no,
            address=self.address,
            postal_code=self.postal_code,
            contact_name=self.contact_name,
            contact_phone=PhoneNumber(self.contact_phone) if self.contact_phone else None,
            contact_email=Email(self.contact_email) if self.contact_email else None,
            website=self.website,
        )

    def validate(self, org_uuid: str) -> Result[OrgDetail, DomainError]:
        return OrgDetail.create(
            org_uuid,
            legal_name=self.legal_name,
            registration_no=self.registration_no,
            address=self.address,
            postal_code=self.postal_code,
            contact_name=self.contact_name,
            contact_phone=self.contact_phone,
            contact_email=self.contact_email,
            website=self.website,
        )


@dataclass(frozen=True, kw_only=True)
class OrganizationModel(EntityModel):
    org_code: str
    org_name: str
    detail: OrgDetailModel = field(default_factory=OrgDetailModel)

    @classmethod
    def from_domain(cls, o: Organization) -> OrganizationModel:
        return cls(
            **entity_fields(o),
            org_code=o.org_code.value,
            org_name=o.org_name,
            detail=OrgDetailModel.from_domain(o.detail),
        )

    def to_domain(self) -> Organization:
        return Organization(
            **entity_kwargs(self),
            org_code=Code(self.org_code),
            org_name=self.org_name,
            detail=self.detail.to_domain(self.org_uuid),
        )


@dataclass(frozen=True, kw_only=True)
class CreateOrganization(CreateMeta):
    org_code: str
    org_name: str
    detail: OrgDetailModel = field(default_factory=OrgDetailModel)
    org_uuid: str = ""  # filled by to_domain(uuid): an organization owns its scope

    def to_domain(self, uuid: str) -> Result[Organization, DomainError]:
        @effect.result[Organization, DomainError]()
        def build() -> Generator[Any, Any, Organization]:
            detail = yield from self.detail.validate(uuid)
            return (
                yield from Organization.create(
                    uuid, self.org_code, self.org_name, detail=detail, description=self.description, remark=self.remark
                )
            )

        return build()


@dataclass(frozen=True, kw_only=True)
class UpdateOrganization(UpdateMeta):
    org_name: str | None = None

    def apply_to(self, org: Organization) -> Result[Organization, DomainError]:
        return org.rename(self.org_name).map(self.apply_meta)
