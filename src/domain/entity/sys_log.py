from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..enum import LogType
from .base import Entity
from .event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class SysLog(Entity):
    """Append-only audit record (``sys_log``)."""

    log_uuid: str
    log_type: LogType = LogType.EVENT
    event_type: str
    aggregate_id: str
    trace_id: str | None = None
    content: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @staticmethod
    def from_event(log_uuid: str, event: DomainEvent, content: dict[str, Any], trace_id: str | None) -> SysLog:
        return SysLog(
            org_uuid=event.org_uuid,
            log_uuid=log_uuid,
            log_type=LogType.EVENT,
            event_type=event.event_type(),
            aggregate_id=event.aggregate_id,
            trace_id=trace_id,
            content=content,
            occurred_at=event.occurred_at,
        )
