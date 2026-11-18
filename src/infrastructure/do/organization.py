from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class OrganizationDO(CommonColumns, Base):
    __tablename__ = "organization"
    __table_args__ = (
        org_index("organization"),
        unique_alive("uk_organization_org_uuid", "org_uuid"),
        unique_alive("uk_organization_org_code", "org_code"),
        {"comment": "組織テーブル"},
    )

    org_code: Mapped[str] = mapped_column(String(64), comment="組織コード")
    org_name: Mapped[str] = mapped_column(String(128), comment="組織名")


class OrgDetailDO(CommonColumns, Base):
    __tablename__ = "org_detail"
    __table_args__ = (
        org_index("org_detail"),
        unique_alive("uk_org_detail_org_uuid", "org_uuid"),
        {"comment": "組織詳細テーブル (organization と 1:1)"},
    )

    legal_name: Mapped[str | None] = mapped_column(String(255), comment="正式名称")
    registration_no: Mapped[str | None] = mapped_column(String(64), comment="法人番号")
    address: Mapped[str | None] = mapped_column(String(512), comment="住所")
    postal_code: Mapped[str | None] = mapped_column(String(16), comment="郵便番号")
    contact_name: Mapped[str | None] = mapped_column(String(128), comment="担当者名")
    contact_phone: Mapped[str | None] = mapped_column(String(32), comment="担当者電話番号")
    contact_email: Mapped[str | None] = mapped_column(String(255), comment="担当者メールアドレス")
    website: Mapped[str | None] = mapped_column(String(255), comment="Webサイト")
