from sqlalchemy import Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class SysConfigDO(CommonColumns, Base):
    __tablename__ = "sys_config"
    __table_args__ = (
        org_index("sys_config"),
        Index("idx_02_sys_config_group", "config_group"),
        unique_alive("uk_sys_config_config_uuid", "config_uuid"),
        unique_alive("uk_sys_config_org_key", "org_uuid", "config_key"),
        {"comment": "システム設定テーブル"},
    )

    config_uuid: Mapped[str] = mapped_column(String(64), comment="設定UUID")
    config_key: Mapped[str] = mapped_column(String(128), comment="設定キー")
    config_value: Mapped[str] = mapped_column(Text, comment="設定値")
    value_type: Mapped[str] = mapped_column(
        String(16), server_default="string", default="string", comment="値種別 (string/int/bool/json)"
    )
    config_group: Mapped[str | None] = mapped_column(String(64), comment="設定グループ")
