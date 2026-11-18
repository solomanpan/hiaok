"""``organization`` (root) + ``org_detail`` (1:1 entity)."""

from __future__ import annotations

from ...domain.entity import Organization, OrgDetail
from ...domain.vo import Code, Email, PhoneNumber, text_or_none
from ..database import RoutingDatabase
from ..do import OrganizationDO, OrgDetailDO
from .base import EntityDao, entity_kwargs


class OrgDetailDao(EntityDao[OrgDetailDO, OrgDetail]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, OrgDetailDO, "org_uuid")

    def to_entity(self, do: OrgDetailDO) -> OrgDetail:
        return OrgDetail(
            **entity_kwargs(do),
            legal_name=do.legal_name,
            registration_no=do.registration_no,
            address=do.address,
            postal_code=do.postal_code,
            contact_name=do.contact_name,
            contact_phone=PhoneNumber(do.contact_phone) if do.contact_phone else None,
            contact_email=Email(do.contact_email) if do.contact_email else None,
            website=do.website,
        )

    def to_do(self, entity: OrgDetail, do: OrgDetailDO | None = None) -> OrgDetailDO:
        target = self.new_or(do, entity)
        target.legal_name = entity.legal_name
        target.registration_no = entity.registration_no
        target.address = entity.address
        target.postal_code = entity.postal_code
        target.contact_name = entity.contact_name
        target.contact_phone = text_or_none(entity.contact_phone)
        target.contact_email = text_or_none(entity.contact_email)
        target.website = entity.website
        return target


class OrganizationDao(EntityDao[OrganizationDO, Organization]):
    def __init__(self, db: RoutingDatabase, details: OrgDetailDao | None = None) -> None:
        super().__init__(db, OrganizationDO, "org_uuid")
        self._details = details or OrgDetailDao(db)

    def to_entity(self, do: OrganizationDO, *, detail: OrgDetailDO | None = None) -> Organization:
        return Organization(
            **entity_kwargs(do),
            org_code=Code(do.org_code),
            org_name=do.org_name,
            detail=self._details.to_entity(detail) if detail else OrgDetail.empty(do.org_uuid),
        )

    def to_do(self, entity: Organization, do: OrganizationDO | None = None) -> OrganizationDO:
        """Root row only; ``org_detail`` is written by ``OrgDetailDao``."""
        target = self.new_or(do, entity)
        target.org_code = entity.org_code.value
        target.org_name = entity.org_name
        return target
