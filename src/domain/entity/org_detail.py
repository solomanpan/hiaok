from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Result, effect
from hiaok_core.exception import DomainError

from ..vo import Email, PhoneNumber
from .base import Entity


@dataclass(frozen=True, kw_only=True)
class OrgDetail(Entity):
    """``org_detail`` (1:1 with Organization, identity = org_uuid). Lives inside the Organization aggregate."""

    legal_name: str | None = None
    registration_no: str | None = None
    address: str | None = None
    postal_code: str | None = None
    contact_name: str | None = None
    contact_phone: PhoneNumber | None = None
    contact_email: Email | None = None
    website: str | None = None

    @staticmethod
    def empty(org_uuid: str) -> OrgDetail:
        return OrgDetail(org_uuid=org_uuid)

    @staticmethod
    def create(
        org_uuid: str,
        *,
        legal_name: str | None = None,
        registration_no: str | None = None,
        address: str | None = None,
        postal_code: str | None = None,
        contact_name: str | None = None,
        contact_phone: str | None = None,
        contact_email: str | None = None,
        website: str | None = None,
    ) -> Result[OrgDetail, DomainError]:
        @effect.result[OrgDetail, DomainError]()
        def build() -> Generator[Any, Any, OrgDetail]:
            phone = yield from PhoneNumber.optional(contact_phone)
            email = yield from Email.optional(contact_email)
            return OrgDetail(
                org_uuid=org_uuid,
                legal_name=legal_name,
                registration_no=registration_no,
                address=address,
                postal_code=postal_code,
                contact_name=contact_name,
                contact_phone=phone,
                contact_email=email,
                website=website,
            )

        return build()
