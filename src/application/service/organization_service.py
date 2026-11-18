from __future__ import annotations

from expression import Result
from hiaok_core.exception import DomainError
from hiaok_core.fp import AsyncResult

from ...domain.entity import Organization
from ..model import OrgDetailModel
from .base import CrudService
from .datasource import master


class OrganizationService(CrudService[Organization]):
    entity = "Organization"

    @master
    async def update_detail(self, org_uuid: str, detail: OrgDetailModel) -> Result[Organization, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, org_uuid))
            .bind(lambda org: detail.validate(org.org_uuid).map(org.update_detail))
            .bind(self.save)
        )
