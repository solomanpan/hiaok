from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class ProjectDO(CommonColumns, Base):
    __tablename__ = "project"
    __table_args__ = (
        org_index("project"),
        Index("idx_02_project_tenant_uuid", "tenant_uuid"),
        unique_alive("uk_project_project_uuid", "project_uuid"),
        unique_alive("uk_project_tenant_code", "tenant_uuid", "project_code"),
        {"comment": "プロジェクトテーブル"},
    )

    tenant_uuid: Mapped[str] = mapped_column(String(64), comment="テナントUUID")
    project_uuid: Mapped[str] = mapped_column(String(64), comment="プロジェクトUUID")
    project_code: Mapped[str] = mapped_column(String(64), comment="プロジェクトコード")
    project_name: Mapped[str] = mapped_column(String(128), comment="プロジェクト名")
    owner_user_uuid: Mapped[str | None] = mapped_column(String(64), comment="オーナーユーザーUUID")
