from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

from ...domain.entity import SysLog
from ...domain.enum import LogType
from .base import EntityModel, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class SysLogModel(EntityModel):
    log_uuid: str
    log_type: str
    event_type: str
    aggregate_id: str
    trace_id: str | None = None
    content: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime | None = None

    @classmethod
    def from_domain(cls, log: SysLog) -> SysLogModel:
        return cls(
            **entity_fields(log),
            log_uuid=log.log_uuid,
            log_type=log.log_type.value,
            event_type=log.event_type,
            aggregate_id=log.aggregate_id,
            trace_id=log.trace_id,
            content=log.content,
            occurred_at=log.occurred_at,
        )

    def to_domain(self) -> SysLog:
        log = SysLog(
            **entity_kwargs(self),
            log_uuid=self.log_uuid,
            log_type=LogType(self.log_type),
            event_type=self.event_type,
            aggregate_id=self.aggregate_id,
            trace_id=self.trace_id,
            content=self.content,
        )
        return log if self.occurred_at is None else replace(log, occurred_at=self.occurred_at)
