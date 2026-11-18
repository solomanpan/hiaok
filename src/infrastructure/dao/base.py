"""Table-level data access on data objects (DO). Every query filters ``delete_flag = 0``.

* ``BaseDao[D]``         - queries / writes on one table.
* ``EntityDao[D, E]``    - plus the DO <-> entity conversion: ``to_entity(do)`` / ``to_do(entity, do=None)``.

DAOs never open sessions: they use the session of the current ``@master``/``@slave`` scope.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, cast

from hiaok_core.context import current_context
from sqlalchemy import ColumnElement, Select, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entity import Entity
from ...domain.enum import Status
from ...domain.vo import Audit
from ..database import CommonColumns, RoutingDatabase


class BaseDao[D: CommonColumns]:
    """``org_uuid`` is positional-only everywhere so it can also be used as a filter column
    (the ``organization`` table's own uuid column *is* ``org_uuid``)."""

    def __init__(self, db: RoutingDatabase, do_type: type[D], uuid_column: str) -> None:
        self._db = db
        self.do_type = do_type
        self.uuid_column = uuid_column

    @property
    def session(self) -> AsyncSession:
        return self._db.session

    def col(self, name: str) -> Any:
        return getattr(self.do_type, name)

    # ---------------------------------------------------------------- query building
    def _where(self, org_uuid: str | None, /, **eq: Any) -> list[ColumnElement[bool]]:
        conds: list[ColumnElement[bool]] = [self.do_type.delete_flag == 0]
        if org_uuid is not None:
            conds.append(self.do_type.org_uuid == org_uuid)
        conds.extend(self.col(k) == v for k, v in eq.items())
        return conds

    def select(self, org_uuid: str | None, /, **eq: Any) -> Select[Any]:
        return select(self.do_type).where(*self._where(org_uuid, **eq))

    # ---------------------------------------------------------------- reads
    async def get(self, org_uuid: str | None, uuid: str) -> D | None:
        return await self.find_one(org_uuid, **{self.uuid_column: uuid})

    async def find_one(self, org_uuid: str | None, /, **eq: Any) -> D | None:
        return cast(D | None, (await self.session.execute(self.select(org_uuid, **eq).limit(1))).scalar_one_or_none())

    async def list_where(self, org_uuid: str | None, /, **eq: Any) -> list[D]:
        rows = await self.session.execute(self.select(org_uuid, **eq).order_by(self.do_type.id))
        return cast(list[D], list(rows.scalars()))

    async def list_in(self, org_uuid: str | None, column: str, values: Iterable[str]) -> list[D]:
        values = list(values)
        if not values:
            return []
        stmt = self.select(org_uuid).where(self.col(column).in_(values)).order_by(self.do_type.id)
        return cast(list[D], list((await self.session.execute(stmt)).scalars()))

    async def page(
        self, org_uuid: str | None, offset: int, limit: int, /, *, newest_first: bool = False, **eq: Any
    ) -> tuple[list[D], int]:
        conds = self._where(org_uuid, **eq)
        total = (await self.session.execute(select(func.count()).select_from(self.do_type).where(*conds))).scalar_one()
        order = self.do_type.id.desc() if newest_first else self.do_type.id
        stmt = select(self.do_type).where(*conds).order_by(order).offset(offset).limit(limit)
        rows = await self.session.execute(stmt)
        return cast(list[D], list(rows.scalars())), int(total)

    # ---------------------------------------------------------------- writes
    def add(self, do: D) -> D:
        do.opr = current_context().operator
        self.session.add(do)
        return do

    async def soft_delete(self, org_uuid: str | None, /, **eq: Any) -> int:
        stmt = (
            update(self.do_type)
            .where(*self._where(org_uuid, **eq))
            .values(delete_flag=1, opr=current_context().operator)
            .execution_options(synchronize_session="fetch")
        )
        result = await self.session.execute(stmt)
        return int(getattr(result, "rowcount", 0) or 0)


class LinkDao[D: CommonColumns](BaseDao[D]):
    """Association tables (user_role / role_permission / menu_role): diff-based sync with soft delete."""

    async def sync(
        self,
        org_uuid: str,
        owner: tuple[str, str],
        key_columns: Sequence[str],
        desired: set[tuple[str, ...]],
        extra: dict[str, Any] | None = None,
    ) -> None:
        owner_col, owner_uuid = owner
        current = {
            tuple(getattr(r, c) for c in key_columns): r
            for r in await self.list_where(org_uuid, **{owner_col: owner_uuid})
        }
        operator = current_context().operator
        for key, row in current.items():
            if key not in desired:
                row.delete_flag = 1
                row.opr = operator
        for key in desired - current.keys():
            values = {
                "org_uuid": org_uuid,
                owner_col: owner_uuid,
                **dict(zip(key_columns, key, strict=True)),
                **(extra or {}),
            }
            self.add(self.do_type(**values))


# ---------------------------------------------------------------- DO <-> entity
def audit_of(do: CommonColumns) -> Audit:
    return Audit(create_time=do.create_time, update_time=do.update_time, opr=do.opr)


def entity_kwargs(do: CommonColumns) -> dict[str, Any]:
    """Common columns -> ``Entity`` constructor kwargs."""
    return {
        "org_uuid": do.org_uuid,
        "description": do.description,
        "remark": do.remark,
        "state": Status(do.state),
        "audit": audit_of(do),
    }


def fill_common(do: CommonColumns, entity: Entity) -> None:
    do.org_uuid = entity.org_uuid
    do.description = entity.description
    do.remark = entity.remark
    do.state = int(entity.state)


class EntityDao[D: CommonColumns, E: Entity](BaseDao[D], ABC):
    """A DAO whose rows map to one entity type."""

    @abstractmethod
    def to_entity(self, do: D) -> E:
        """DO -> entity (trusted: values come from the database, no re-validation)."""

    @abstractmethod
    def to_do(self, entity: E, do: D | None = None) -> D:
        """entity -> DO. Fills ``do`` (a loaded row => UPDATE) or a new instance (=> INSERT)."""

    def new_or(self, do: D | None, entity: E) -> D:
        """Helper for ``to_do``: the row to fill, with the common columns already copied."""
        target = do if do is not None else self.do_type()
        fill_common(target, entity)
        return target
