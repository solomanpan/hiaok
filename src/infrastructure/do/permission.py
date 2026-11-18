from sqlalchemy import Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class PermissionDO(CommonColumns, Base):
    __tablename__ = "permission"
    __table_args__ = (
        org_index("permission"),
        Index("idx_02_permission_menu_uuid", "menu_uuid"),
        unique_alive("uk_permission_permission_uuid", "permission_uuid"),
        unique_alive("uk_permission_org_code", "org_uuid", "perm_code"),
        {"comment": "権限テーブル"},
    )

    permission_uuid: Mapped[str] = mapped_column(String(64), comment="権限UUID")
    perm_code: Mapped[str] = mapped_column(String(128), comment="権限コード (例: project:create)")
    perm_name: Mapped[str] = mapped_column(String(128), comment="権限名")
    perm_type: Mapped[int] = mapped_column(
        SmallInteger, server_default="0", default=0, comment="権限種別 (0:API 1:ボタン 2:データ)"
    )
    resource: Mapped[str | None] = mapped_column(String(128), comment="リソース")
    action: Mapped[str | None] = mapped_column(String(64), comment="アクション")
    menu_uuid: Mapped[str | None] = mapped_column(String(64), comment="所属メニューUUID")
