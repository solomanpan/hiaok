from __future__ import annotations

from datetime import datetime
from typing import Any

from ...application.model import SysLogModel
from .common import EntityResponse


class SysLogResponse(EntityResponse):
    log_uuid: str
    log_type: str
    event_type: str
    aggregate_id: str
    trace_id: str | None = None
    content: dict[str, Any]
    occurred_at: datetime | None = None

    @classmethod
    def of(cls, m: SysLogModel) -> SysLogResponse:
        return cls.model_validate(m)
