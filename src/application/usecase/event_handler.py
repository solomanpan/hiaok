"""Event-driven usecases (consumers). Brokers deliver at-least-once -> handlers must be idempotent."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any

from hiaok_core.context import current_context
from hiaok_core.facade import Cache, EventHandler, EventSubscriber
from hiaok_core.fp import curry
from hiaok_core.json import to_jsonable

from ...domain.entity import SysLog
from ...domain.entity.event import (
    DomainEvent,
    EntityCreated,
    EntityDeleted,
    EntityUpdated,
    RoleMenusChanged,
    RolePermissionsChanged,
    SysConfigChanged,
    UserRolesAssigned,
    WriteRequested,
    all_event_types,
)
from ..service import AuthService, SysLogService, config_cache_key

_BASE_FIELDS = {"org_uuid", "event_id", "occurred_at"}


def event_content(event: DomainEvent) -> dict[str, Any]:
    payload = {k: v for k, v in asdict(event).items() if k not in _BASE_FIELDS}
    return {"event_id": event.event_id, **to_jsonable(payload)}


@curry
async def record_audit_log(logs: SysLogService, event: DomainEvent) -> None:
    """Every domain event -> one ``sys_log`` row. log_uuid is derived from event_id => replay-safe."""
    log_uuid = uuid.uuid5(uuid.NAMESPACE_URL, f"hiaok:event:{event.event_id}").hex
    await logs.append(SysLog.from_event(log_uuid, event, event_content(event), current_context().trace_id))


@curry
async def evict_config_cache(cache: Cache, event: SysConfigChanged) -> None:
    await cache.delete(config_cache_key(event.org_uuid, event.config_key))


# changing any of these changes what some user may do
_AUTHORITY_ENTITIES = {"User", "UserGroup", "Role", "Permission"}


@curry
async def evict_authorities(auth: AuthService, event: DomainEvent) -> None:
    if (
        isinstance(event, EntityCreated | EntityUpdated | EntityDeleted)
        and event.entity_type not in _AUTHORITY_ENTITIES
    ):
        return
    await auth.invalidate_authorities(event.org_uuid)


def subscribe_event_handlers(
    bus: EventSubscriber, logs: SysLogService, cache: Cache, on_write: EventHandler[WriteRequested] | None = None
) -> None:
    """``on_write`` executes accepted write requests (see ``usecase.command``); every other event is audited."""
    # importing src.domain.entity.event registered every event type before this runs
    for event_type in all_event_types():
        if event_type is not WriteRequested:  # its outcome row (success / failure) is the audit record
            bus.subscribe(event_type, record_audit_log(logs))
    if on_write is not None:
        bus.subscribe(WriteRequested, on_write)
    bus.subscribe(SysConfigChanged, evict_config_cache(cache))
    auth = AuthService(cache)
    for event_type in (
        EntityCreated,
        EntityUpdated,
        EntityDeleted,
        UserRolesAssigned,
        RolePermissionsChanged,
        RoleMenusChanged,
    ):
        bus.subscribe(event_type, evict_authorities(auth))
