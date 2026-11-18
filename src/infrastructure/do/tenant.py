from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class TenantDO(CommonColumns, Base):
    __tablename__ = "tenant"
    __table_args__ = (
        org_index("tenant"),
        unique_alive("uk_tenant_tenant_uuid", "tenant_uuid"),
        unique_alive("uk_tenant_org_code", "org_uuid", "tenant_code"),
        {"comment": "テナントテーブル"},
    )

    tenant_uuid: Mapped[str] = mapped_column(String(64), comment="テナントUUID")
    tenant_code: Mapped[str] = mapped_column(String(64), comment="テナントコード")
    tenant_name: Mapped[str] = mapped_column(String(128), comment="テナント名")
    expire_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="有効期限")
