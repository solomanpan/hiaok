from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class SysLogDO(CommonColumns, Base):
    __tablename__ = "sys_log"
    __table_args__ = (
        org_index("sys_log"),
        Index("idx_02_sys_log_event_type", "event_type"),
        Index("idx_03_sys_log_aggregate_id", "aggregate_id"),
        Index("idx_04_sys_log_occurred_at", "occurred_at"),
        unique_alive("uk_sys_log_log_uuid", "log_uuid"),
        {"comment": "システムログ (監査) テーブル"},
    )

    log_uuid: Mapped[str] = mapped_column(String(64), comment="ログUUID")
    log_type: Mapped[str] = mapped_column(String(32), comment="ログ種別 (event/operation/login)")
    event_type: Mapped[str] = mapped_column(String(128), comment="イベント種別")
    aggregate_id: Mapped[str] = mapped_column(String(64), comment="集約ID")
    trace_id: Mapped[str | None] = mapped_column(String(64), comment="トレースID")
    content: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}", comment="内容 (JSON)")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), comment="発生日時")
