"""Declarative base + the common columns every table carries."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Index, MetaData, SmallInteger, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

NAMING = {
    "ix": "idx_%(table_name)s_%(column_0_N_name)s",
    "uq": "uk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


class CommonColumns:
    """id / org_uuid / create_time / update_time / description / state / remark / opr / delete_flag."""

    __mapper_args__ = {"eager_defaults": True}  # fetch create_time/update_time via RETURNING

    id: Mapped[int] = mapped_column(
        BigInteger, Identity(always=False), primary_key=True, sort_order=-100, comment="ID (自動採番)"
    )

    @declared_attr
    def org_uuid(cls) -> Mapped[str]:
        return mapped_column(String(64), nullable=False, sort_order=-90, comment="組織UUID")

    create_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, sort_order=90, comment="作成日時"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        # No trigger: PostgreSQL has no "ON UPDATE CURRENT_TIMESTAMP", so SQLAlchemy adds
        # ``update_time=now()`` to every UPDATE it emits (ORM flush and Core ``update()``).
        # Raw SQL that bypasses SQLAlchemy must set update_time itself.
        onupdate=func.now(),
        nullable=False,
        sort_order=91,
        comment="更新日時",
    )
    description: Mapped[str | None] = mapped_column(String(512), sort_order=92, comment="説明")
    state: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="0", default=0, sort_order=93, comment="状態 (0:有効 1:無効)"
    )
    remark: Mapped[str | None] = mapped_column(String(255), sort_order=94, comment="備考")
    opr: Mapped[str | None] = mapped_column(String(255), sort_order=95, comment="操作者")
    delete_flag: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
        server_default="0",
        default=0,
        sort_order=96,
        comment="削除フラグ (0:未削除 1:削除済)",
    )


ALIVE = "delete_flag = 0"


def org_index(table: str) -> Index:
    """``idx_01_<table>_org_uuid`` on every table."""
    return Index(f"idx_01_{table}_org_uuid", "org_uuid")


def unique_alive(name: str, *columns: str) -> Index:
    """Unique among non-deleted rows (soft delete frees the value again)."""
    return Index(name, *columns, unique=True, postgresql_where=text(ALIVE))
