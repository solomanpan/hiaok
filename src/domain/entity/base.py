"""Entity building blocks.

Every table carries the same common columns, so ``Entity`` owns them:
``org_uuid / description / remark / state`` (business) and ``audit`` (read-only, filled by persistence).
An aggregate root is simply the entity that owns a consistency boundary (it may hold other entities / VOs).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Self

from expression import Ok, Result
from hiaok_core.exception import DomainError

from ..enum import Status
from ..vo.base import Audit
from .event import DomainEvent, EntityCreated, EntityUpdated


@dataclass(frozen=True, kw_only=True)
class Entity:
    org_uuid: str
    description: str | None = None
    remark: str | None = None
    state: Status = Status.ENABLED
    audit: Audit = field(default_factory=Audit, compare=False)

    @property
    def enabled(self) -> bool:
        return self.state is Status.ENABLED


@dataclass(frozen=True, kw_only=True)
class AggregateRoot(Entity):
    """Immutable aggregate: every state change returns a *new* instance carrying new events."""

    events: tuple[DomainEvent, ...] = field(default=(), compare=False, repr=False)

    @property
    def uuid(self) -> str:  # each aggregate exposes its own *_uuid as the identity
        raise NotImplementedError

    @classmethod
    def entity_type(cls) -> str:
        return cls.__name__

    # ---- events ----
    def record(self, *events: DomainEvent) -> Self:
        return replace(self, events=(*self.events, *events))

    def pull_events(self) -> tuple[Self, tuple[DomainEvent, ...]]:
        return replace(self, events=()), self.events

    def created(self) -> Self:
        return self.record(EntityCreated(org_uuid=self.org_uuid, entity_type=self.entity_type(), entity_uuid=self.uuid))

    # ---- generic changes ----
    def changed(self, **changes: Any) -> Self:
        """Apply only real changes and record ``EntityUpdated`` with the changed field names."""
        diff = {k: v for k, v in changes.items() if getattr(self, k) != v}
        if not diff:
            return self
        return replace(self, **diff).record(
            EntityUpdated(
                org_uuid=self.org_uuid,
                entity_type=self.entity_type(),
                entity_uuid=self.uuid,
                changed_fields=tuple(sorted(diff)),
            )
        )

    def change_meta(
        self, *, description: str | None = None, remark: str | None = None, state: Status | None = None
    ) -> Self:
        """``None`` = keep current value."""
        changes: dict[str, Any] = {}
        if description is not None:
            changes["description"] = description
        if remark is not None:
            changes["remark"] = remark
        if state is not None:
            changes["state"] = state
        return self.changed(**changes)

    def ensure_deletable(self) -> Result[Self, DomainError]:
        return Ok(self)
