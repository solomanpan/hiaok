from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class DepartmentDO(CommonColumns, Base):
    __tablename__ = "department"
    __table_args__ = (
        org_index("department"),
        Index("idx_02_department_parent", "parent_department_uuid"),
        Index("idx_03_department_employee_uuid", "employee_uuid"),
        unique_alive("uk_department_department_uuid", "department_uuid"),
        unique_alive("uk_department_org_code", "org_uuid", "department_code"),
        {"comment": "部署テーブル"},
    )

    department_uuid: Mapped[str] = mapped_column(String(64), comment="部署UUID")
    parent_department_uuid: Mapped[str | None] = mapped_column(String(64), comment="親部署UUID")
    department_code: Mapped[str] = mapped_column(String(64), comment="部署コード")
    department_name: Mapped[str] = mapped_column(String(128), comment="部署名")
    employee_uuid: Mapped[str | None] = mapped_column(String(64), comment="部署責任者 社員UUID")
    sort_order: Mapped[int] = mapped_column(Integer, server_default="0", default=0, comment="表示順")
