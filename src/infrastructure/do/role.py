from sqlalchemy import Index, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class RoleDO(CommonColumns, Base):
    __tablename__ = "role"
    __table_args__ = (
        org_index("role"),
        Index("idx_02_role_tenant_uuid", "tenant_uuid"),
        unique_alive("uk_role_role_uuid", "role_uuid"),
        unique_alive("uk_role_tenant_code", "tenant_uuid", "role_code"),
        {"comment": "ロールテーブル"},
    )

    tenant_uuid: Mapped[str] = mapped_column(String(64), comment="テナントUUID")
    role_uuid: Mapped[str] = mapped_column(String(64), comment="ロールUUID")
    role_code: Mapped[str] = mapped_column(String(64), comment="ロールコード")
    role_name: Mapped[str] = mapped_column(String(128), comment="ロール名")
    role_type: Mapped[int] = mapped_column(
        SmallInteger, server_default="1", default=1, comment="ロール種別 (0:システム 1:カスタム)"
    )


class RolePermissionDO(CommonColumns, Base):
    __tablename__ = "role_permission"
    __table_args__ = (
        org_index("role_permission"),
        Index("idx_02_role_permission_role_uuid", "role_uuid"),
        Index("idx_03_role_permission_perm_uuid", "permission_uuid"),
        unique_alive("uk_role_permission", "role_uuid", "permission_uuid"),
        {"comment": "ロール権限関連テーブル"},
    )

    role_uuid: Mapped[str] = mapped_column(String(64), comment="ロールUUID")
    permission_uuid: Mapped[str] = mapped_column(String(64), comment="権限UUID")


class MenuRoleDO(CommonColumns, Base):
    __tablename__ = "menu_role"
    __table_args__ = (
        org_index("menu_role"),
        Index("idx_02_menu_role_menu_uuid", "menu_uuid"),
        Index("idx_03_menu_role_role_uuid", "role_uuid"),
        unique_alive("uk_menu_role", "menu_uuid", "role_uuid"),
        {"comment": "メニューロール関連テーブル"},
    )

    menu_uuid: Mapped[str] = mapped_column(String(64), comment="メニューUUID")
    role_uuid: Mapped[str] = mapped_column(String(64), comment="ロールUUID")
