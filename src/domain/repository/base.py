"""Repository interface. Implemented in ``infrastructure/repository``.

All reads are scoped by ``org_uuid`` (multi-tenant isolation at query level).
``save`` returns ``Error(conflict)`` when a unique constraint is hit instead of raising.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from expression import Option, Result
from hiaok_core.exception import DomainError

from ..entity.base import AggregateRoot
from .page import Page, PageQuery


class Repository[A: AggregateRoot](Protocol):
    async def get(self, org_uuid: str, uuid: str) -> Option[A]: ...

    async def list(self, org_uuid: str | None, page: PageQuery) -> Page[A]: ...

    async def list_all(self, org_uuid: str) -> list[A]: ...

    async def list_by_uuids(self, org_uuid: str, uuids: Iterable[str]) -> list[A]: ...

    async def save(self, aggregate: A) -> Result[A, DomainError]:
        """Returns the aggregate with ``audit`` refreshed (create_time / update_time / opr)."""
        ...

    async def delete(self, org_uuid: str, uuid: str) -> bool: ...
