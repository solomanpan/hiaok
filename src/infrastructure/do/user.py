from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class UserDO(CommonColumns, Base):
    # NOTE: "user" is a reserved word in PostgreSQL. SQLAlchemy quotes it automatically;
    # hand-written SQL must use "user" (SELECT * FROM user returns current_user!).
    __tablename__ = "user"
    __table_args__ = (
        org_index("user"),
        Index("idx_02_user_tenant_uuid", "tenant_uuid"),
        Index("idx_03_user_group_uuid", "group_uuid"),
        unique_alive("uk_user_user_uuid", "user_uuid"),
        unique_alive("uk_user_tenant_username", "tenant_uuid", "username"),
        {"comment": "ユーザーテーブル"},
    )

    tenant_uuid: Mapped[str] = mapped_column(String(64), comment="テナントUUID")
    user_uuid: Mapped[str] = mapped_column(String(64), comment="ユーザーUUID")
    group_uuid: Mapped[str | None] = mapped_column(String(64), comment="所属グループUUID")
    username: Mapped[str] = mapped_column(String(64), comment="ログインID")
    password_hash: Mapped[str] = mapped_column(String(255), comment="パスワードハッシュ")
    email: Mapped[str | None] = mapped_column(String(255), comment="メールアドレス")
    phone: Mapped[str | None] = mapped_column(String(32), comment="電話番号")
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), comment="最終ログイン日時")


class UserDetailDO(CommonColumns, Base):
    __tablename__ = "user_detail"
    __table_args__ = (
        org_index("user_detail"),
        unique_alive("uk_user_detail_user_uuid", "user_uuid"),
        {"comment": "ユーザー詳細テーブル (user と 1:1)"},
    )

    user_uuid: Mapped[str] = mapped_column(String(64), comment="ユーザーUUID")
    nickname: Mapped[str | None] = mapped_column(String(128), comment="ニックネーム")
    real_name: Mapped[str | None] = mapped_column(String(128), comment="氏名")
    avatar_url: Mapped[str | None] = mapped_column(String(512), comment="アバターURL")
    gender: Mapped[str | None] = mapped_column(String(16), comment="性別")
    birthday: Mapped[date | None] = mapped_column(Date, comment="生年月日")
    locale: Mapped[str | None] = mapped_column(String(16), comment="ロケール")
    timezone: Mapped[str | None] = mapped_column(String(64), comment="タイムゾーン")


class UserRoleDO(CommonColumns, Base):
    __tablename__ = "user_role"
    __table_args__ = (
        org_index("user_role"),
        Index("idx_02_user_role_user_uuid", "user_uuid"),
        Index("idx_03_user_role_role_uuid", "role_uuid"),
        unique_alive("uk_user_role", "user_uuid", "role_uuid", "project_uuid"),
        {"comment": "ユーザーロール関連テーブル"},
    )

    tenant_uuid: Mapped[str] = mapped_column(String(64), comment="テナントUUID")
    user_uuid: Mapped[str] = mapped_column(String(64), comment="ユーザーUUID")
    role_uuid: Mapped[str] = mapped_column(String(64), comment="ロールUUID")
    project_uuid: Mapped[str] = mapped_column(
        String(64), server_default="", default="", comment="プロジェクトUUID (空文字:テナント全体)"
    )
