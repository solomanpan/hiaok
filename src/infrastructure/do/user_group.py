from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class UserGroupDO(CommonColumns, Base):
    __tablename__ = "user_group"
    __table_args__ = (
        org_index("user_group"),
        Index("idx_02_user_group_tenant_uuid", "tenant_uuid"),
        Index("idx_03_user_group_parent", "parent_group_uuid"),
        unique_alive("uk_user_group_group_uuid", "group_uuid"),
        unique_alive("uk_user_group_tenant_code", "tenant_uuid", "group_code"),
        {"comment": "ユーザーグループテーブル"},
    )

    tenant_uuid: Mapped[str] = mapped_column(String(64), comment="テナントUUID")
    group_uuid: Mapped[str] = mapped_column(String(64), comment="グループUUID")
    parent_group_uuid: Mapped[str | None] = mapped_column(String(64), comment="親グループUUID")
    group_code: Mapped[str] = mapped_column(String(64), comment="グループコード")
    group_name: Mapped[str] = mapped_column(String(128), comment="グループ名")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", default=0, comment="表示順")
