"""Application models: the boundary objects between use cases and the domain.

* ``XxxModel``  - read model.   ``from_domain(aggregate)`` / ``to_domain()`` (trusted rebuild, e.g. from cache)
* ``CreateXxx`` - command.      ``to_domain(uuid) -> Result[Aggregate, DomainError]`` (validates)
* ``UpdateXxx`` - command.      ``apply_to(aggregate) -> Result[Aggregate, DomainError]`` (None = unchanged)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import AggregateRoot, Entity
from ...domain.enum import Status
from ...domain.service.tree import TreeNode
from ...domain.vo import Audit


class CreateCommand[A](Protocol):
    def to_domain(self, uuid: str, /) -> Result[A, DomainError]: ...


class UpdateCommand[A](Protocol):
    def apply_to(self, aggregate: A, /) -> Result[A, DomainError]: ...


@dataclass(frozen=True, kw_only=True)
class EntityModel:
    """Common columns of every table."""

    org_uuid: str
    description: str | None = None
    remark: str | None = None
    state: int = Status.ENABLED
    create_time: datetime | None = None
    update_time: datetime | None = None
    opr: str | None = None


def entity_fields(e: Entity) -> dict[str, Any]:
    """domain -> model kwargs"""
    return {
        "org_uuid": e.org_uuid,
        "description": e.description,
        "remark": e.remark,
        "state": int(e.state),
        "create_time": e.audit.create_time,
        "update_time": e.audit.update_time,
        "opr": e.audit.opr,
    }


def entity_kwargs(m: EntityModel) -> dict[str, Any]:
    """model -> domain kwargs"""
    return {
        "org_uuid": m.org_uuid,
        "description": m.description,
        "remark": m.remark,
        "state": Status(m.state),
        "audit": Audit(create_time=m.create_time, update_time=m.update_time, opr=m.opr),
    }


@dataclass(frozen=True, kw_only=True)
class CreateMeta:
    description: str | None = None
    remark: str | None = None


@dataclass(frozen=True, kw_only=True)
class UpdateMeta:
    description: str | None = None
    remark: str | None = None
    state: int | None = None

    def apply_meta[A: AggregateRoot](self, aggregate: A) -> A:
        return aggregate.change_meta(
            description=self.description,
            remark=self.remark,
            state=None if self.state is None else Status(self.state),
        )


@dataclass(frozen=True)
class TreeModel[M]:
    item: M
    children: list[TreeModel[M]] = field(default_factory=list)

    @staticmethod
    def from_nodes[T](nodes: list[TreeNode[T]], to_model: Callable[[T], M]) -> list[TreeModel[M]]:
        return [TreeModel(to_model(n.item), TreeModel.from_nodes(list(n.children), to_model)) for n in nodes]
