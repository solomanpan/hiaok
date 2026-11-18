from __future__ import annotations

from ...domain.entity import Organization
from ..dao import OrganizationDao, OrgDetailDao
from ..database import RoutingDatabase
from ..do import OrganizationDO
from .base import SqlRepository


class SqlOrganizationRepository(SqlRepository[Organization, OrganizationDO]):
    """``organization`` + ``org_detail`` (1:1)."""

    def __init__(self, db: RoutingDatabase) -> None:
        self._details = OrgDetailDao(db)
        self._orgs = OrganizationDao(db, self._details)
        super().__init__(db, self._orgs)

    async def load_many(self, rows: list[OrganizationDO]) -> list[Organization]:
        details = {d.org_uuid: d for d in await self._details.list_in(None, "org_uuid", [r.org_uuid for r in rows])}
        return [self._orgs.to_entity(r, detail=details.get(r.org_uuid)) for r in rows]

    async def save_children(self, aggregate: Organization) -> None:
        existing = await self._details.get(aggregate.org_uuid, aggregate.org_uuid)
        self._details.add(self._details.to_do(aggregate.detail, existing))

    async def delete_children(self, org_uuid: str, uuid: str) -> None:
        await self._details.soft_delete(org_uuid)
