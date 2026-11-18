from sqlalchemy import Boolean, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class MenuDO(CommonColumns, Base):
    __tablename__ = "menu"
    __table_args__ = (
        org_index("menu"),
        Index("idx_02_menu_parent_uuid", "parent_uuid"),
        unique_alive("uk_menu_menu_uuid", "menu_uuid"),
        unique_alive("uk_menu_org_code", "org_uuid", "menu_code"),
        {"comment": "メニューテーブル"},
    )

    menu_uuid: Mapped[str] = mapped_column(String(64), comment="メニューUUID")
    parent_uuid: Mapped[str | None] = mapped_column(String(64), comment="親メニューUUID")
    menu_code: Mapped[str] = mapped_column(String(64), comment="メニューコード")
    menu_name: Mapped[str] = mapped_column(String(128), comment="メニュー名")
    menu_type: Mapped[int] = mapped_column(
        SmallInteger, server_default="1", default=1, comment="メニュー種別 (0:ディレクトリ 1:メニュー 2:ボタン)"
    )
    path: Mapped[str | None] = mapped_column(String(255), comment="ルートパス")
    component: Mapped[str | None] = mapped_column(String(255), comment="コンポーネント")
    icon: Mapped[str | None] = mapped_column(String(128), comment="アイコン")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", default=0, comment="表示順")
    visible: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True, comment="表示フラグ")
