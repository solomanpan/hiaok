from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError, not_found
from hiaok_core.facade import EventPublisher, IdGenerator, TransactionManager, uuid_hex
from hiaok_core.fp import AsyncResult

from ...domain.entity import AggregateRoot
from ...domain.entity.event import DomainEvent, EntityDeleted
from ...domain.repository import Page, PageQuery, Repository
from ..model.base import CreateCommand, UpdateCommand
from .datasource import master, slave


class ApplicationService:
    """Owns the transaction boundary (``@master``/``@slave``) and publishes events after commit."""

    def __init__(self, tx: TransactionManager, publisher: EventPublisher, new_id: IdGenerator = uuid_hex) -> None:
        self._tx = tx
        self._publisher = publisher
        self._new_id = new_id

    @property
    def tx(self) -> TransactionManager:
        return self._tx

    def publish_after_commit(self, events: Iterable[DomainEvent]) -> None:
        pending = tuple(events)
        if not pending:
            return
        current = self._tx.current()
        if current.is_none():
            raise RuntimeError("domain events can only be recorded inside a @master method")

        async def publish() -> None:
            for event in pending:
                await self._publisher.publish(event)

        current.value.after_commit(publish)

    async def persist[A: AggregateRoot](self, repository: Repository[A], aggregate: A) -> Result[A, DomainError]:
        """save -> (after commit) publish the events the aggregate recorded."""
        clean, events = aggregate.pull_events()
        saved = await repository.save(clean)
        if isinstance(saved, Error):
            return saved
        self.publish_after_commit(events)
        return saved


class CrudService[A: AggregateRoot](ApplicationService):
    """Standard lifecycle for one aggregate. Reads -> ``@slave``, writes -> ``@master``."""

    entity: ClassVar[str] = "Entity"

    def __init__(
        self,
        tx: TransactionManager,
        repository: Repository[A],
        publisher: EventPublisher,
        new_id: IdGenerator = uuid_hex,
    ) -> None:
        super().__init__(tx, publisher, new_id)
        self._repo = repository

    # ---------------------------------------------------------------- reads (replica)
    @slave
    async def get(self, org_uuid: str, uuid: str) -> Result[A, DomainError]:
        return await self.load(org_uuid, uuid)

    @slave
    async def list(self, org_uuid: str | None, page: PageQuery) -> Page[A]:
        return await self._repo.list(org_uuid, page)

    @slave
    async def list_all(self, org_uuid: str) -> list[A]:
        return await self._repo.list_all(org_uuid)

    @slave
    async def list_by_uuids(self, org_uuid: str, uuids: Iterable[str]) -> list[A]:
        return await self._repo.list_by_uuids(org_uuid, uuids)

    # ---------------------------------------------------------------- writes (primary)
    @master
    async def create(self, cmd: CreateCommand[A]) -> Result[A, DomainError]:
        return await AsyncResult.of(cmd.to_domain(self._new_id())).bind(self.save)

    @master
    async def update(self, org_uuid: str, uuid: str, cmd: UpdateCommand[A]) -> Result[A, DomainError]:
        return await AsyncResult.of(self.load(org_uuid, uuid)).bind(cmd.apply_to).bind(self.save)

    @master
    async def delete(self, org_uuid: str, uuid: str) -> Result[None, DomainError]:
        return await AsyncResult.of(self.load(org_uuid, uuid)).bind(lambda a: a.ensure_deletable()).bind(self.remove)

    # ---------------------------------------------------------------- helpers (run inside the caller's scope)
    async def load(self, org_uuid: str, uuid: str) -> Result[A, DomainError]:
        return (await self._repo.get(org_uuid, uuid)).to_result(not_found(self.entity, uuid))

    async def save(self, aggregate: A) -> Result[A, DomainError]:
        return await self.persist(self._repo, aggregate)

    async def remove(self, aggregate: A) -> Result[None, DomainError]:
        await self._repo.delete(aggregate.org_uuid, aggregate.uuid)
        self.publish_after_commit(
            [
                EntityDeleted(
                    org_uuid=aggregate.org_uuid, entity_type=aggregate.entity_type(), entity_uuid=aggregate.uuid
                )
            ]
        )
        return Ok(None)
