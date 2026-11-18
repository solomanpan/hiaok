"""Domain events: base class + registry (deserialising broker messages), generic CRUD facts, business events.

Importing this module registers every event class."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, fields
from datetime import UTC, datetime
from typing import ClassVar

from expression import Option, option

_REGISTRY: dict[str, type[DomainEvent]] = {}


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Immutable fact. Subclasses auto-register by class name.

    ``aggregate_field`` names the field holding the aggregate id (Kafka key -> per-aggregate ordering).
    """

    org_uuid: str
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    occurred_at: datetime = field(default_factory=_now)

    aggregate_field: ClassVar[str] = "org_uuid"

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        _REGISTRY[cls.event_type()] = cls

    def __post_init__(self) -> None:
        # JSON round-trips turn tuples into lists; keep events hashable/immutable.
        for f in fields(self):
            value = getattr(self, f.name)
            if isinstance(value, list):
                object.__setattr__(self, f.name, tuple(value))

    @classmethod
    def event_type(cls) -> str:
        return cls.__name__

    @property
    def aggregate_id(self) -> str:
        return str(getattr(self, self.aggregate_field))


def event_class(name: str) -> Option[type[DomainEvent]]:
    return option.of_obj(_REGISTRY.get(name))


def all_event_types() -> list[type[DomainEvent]]:
    return list(_REGISTRY.values())


@dataclass(frozen=True, kw_only=True)
class EntityCreated(DomainEvent):
    aggregate_field: ClassVar[str] = "entity_uuid"
    entity_type: str
    entity_uuid: str


@dataclass(frozen=True, kw_only=True)
class EntityUpdated(DomainEvent):
    aggregate_field: ClassVar[str] = "entity_uuid"
    entity_type: str
    entity_uuid: str
    changed_fields: tuple[str, ...] = ()


@dataclass(frozen=True, kw_only=True)
class EntityDeleted(DomainEvent):
    aggregate_field: ClassVar[str] = "entity_uuid"
    entity_type: str
    entity_uuid: str


# ---------------------------------------------------------------- business events
@dataclass(frozen=True, kw_only=True)
class OrganizationProvisioned(DomainEvent):
    tenant_uuid: str
    admin_role_uuid: str


@dataclass(frozen=True, kw_only=True)
class UserRegistered(DomainEvent):
    aggregate_field: ClassVar[str] = "user_uuid"
    user_uuid: str
    tenant_uuid: str
    username: str


@dataclass(frozen=True, kw_only=True)
class UserRolesAssigned(DomainEvent):
    aggregate_field: ClassVar[str] = "user_uuid"
    user_uuid: str
    role_uuids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class UserPasswordChanged(DomainEvent):
    aggregate_field: ClassVar[str] = "user_uuid"
    user_uuid: str


@dataclass(frozen=True, kw_only=True)
class RolePermissionsChanged(DomainEvent):
    aggregate_field: ClassVar[str] = "role_uuid"
    role_uuid: str
    permission_uuids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class RoleMenusChanged(DomainEvent):
    aggregate_field: ClassVar[str] = "role_uuid"
    role_uuid: str
    menu_uuids: tuple[str, ...]


@dataclass(frozen=True, kw_only=True)
class DepartmentHeadAppointed(DomainEvent):
    aggregate_field: ClassVar[str] = "department_uuid"
    department_uuid: str
    employee_uuid: str | None


@dataclass(frozen=True, kw_only=True)
class EmployeeTransferred(DomainEvent):
    aggregate_field: ClassVar[str] = "employee_uuid"
    employee_uuid: str
    from_department_uuid: str | None
    to_department_uuid: str


@dataclass(frozen=True, kw_only=True)
class EmployeeLinkedToUser(DomainEvent):
    aggregate_field: ClassVar[str] = "employee_uuid"
    employee_uuid: str
    user_uuid: str


@dataclass(frozen=True, kw_only=True)
class SysConfigChanged(DomainEvent):
    aggregate_field: ClassVar[str] = "config_key"
    config_key: str
    config_value: str
