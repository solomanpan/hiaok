"""Generic SQL repository: rows via the DAO, DO <-> entity via ``dao.to_entity`` / ``dao.to_do``,
savepoint around every save."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import replace

from expression import Error, Ok, Option, Result, Some, option
from hiaok_core.exception import DomainError
from sqlalchemy.exc import IntegrityError

from ...domain.entity import AggregateRoot
from ...domain.repository import Page, PageQuery
from ..dao import EntityDao
from ..dao.base import audit_of
from ..database import CommonColumns, RoutingDatabase
from .errors import integrity_to_domain


class SqlRepository[A: AggregateRoot, D: CommonColumns]:
    """Single-table aggregates need nothing but a DAO. Aggregates with child tables override
    ``load_many`` (batch-load children, no N+1) and ``save_children`` / ``delete_children``."""

    def __init__(self, db: RoutingDatabase, dao: EntityDao[D, A]) -> None:
        self._db = db
        self._dao = dao

    # ---------------------------------------------------------------- hooks
    async def load_many(self, rows: list[D]) -> list[A]:
        return [self._dao.to_entity(row) for row in rows]

    async def save_children(self, aggregate: A) -> None:
        return None

    async def delete_children(self, org_uuid: str, uuid: str) -> None:
        return None

    # ---------------------------------------------------------------- reads
    async def get(self, org_uuid: str, uuid: str) -> Option[A]:
        row = await self._dao.get(org_uuid, uuid)
        if row is None:
            return option.NOTHING
        return Some((await self.load_many([row]))[0])

    async def list(self, org_uuid: str | None, page: PageQuery) -> Page[A]:
        rows, total = await self._dao.page(org_uuid, page.offset, page.limit)
        return Page(tuple(await self.load_many(rows)), total, page.offset, page.limit)

    async def list_all(self, org_uuid: str) -> list[A]:
        return await self.load_many(await self._dao.list_where(org_uuid))

    async def list_by_uuids(self, org_uuid: str, uuids: Iterable[str]) -> list[A]:
        return await self.load_many(await self._dao.list_in(org_uuid, self._dao.uuid_column, uuids))

    # ---------------------------------------------------------------- writes
    async def save(self, aggregate: A) -> Result[A, DomainError]:
        session = self._db.session
        try:
            async with session.begin_nested():  # SAVEPOINT: a unique violation leaves the outer tx usable
                existing = await self._dao.get(aggregate.org_uuid, aggregate.uuid)
                row = self._dao.to_do(aggregate, existing)
                self._dao.add(row)  # new row -> INSERT, loaded row -> UPDATE; stamps opr from the request context
                await self.save_children(aggregate)
                await session.flush()
        except IntegrityError as exc:
            error = integrity_to_domain(exc)
            if error is None:
                raise
            return Error(error)
        return Ok(replace(aggregate, audit=audit_of(row)))

    async def delete(self, org_uuid: str, uuid: str) -> bool:
        deleted = await self._dao.soft_delete(org_uuid, **{self._dao.uuid_column: uuid})
        await self.delete_children(org_uuid, uuid)
        return deleted > 0
