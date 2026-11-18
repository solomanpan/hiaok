from datetime import date

from sqlalchemy import Date, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base, CommonColumns, org_index, unique_alive


class EmployeeDO(CommonColumns, Base):
    __tablename__ = "employee"
    __table_args__ = (
        org_index("employee"),
        Index("idx_02_employee_department_uuid", "department_uuid"),
        Index("idx_03_employee_user_uuid", "user_uuid"),
        unique_alive("uk_employee_employee_uuid", "employee_uuid"),
        unique_alive("uk_employee_org_no", "org_uuid", "employee_no"),
        {"comment": "社員テーブル"},
    )

    employee_uuid: Mapped[str] = mapped_column(String(64), comment="社員UUID")
    employee_no: Mapped[str] = mapped_column(String(64), comment="社員番号")
    employee_name: Mapped[str] = mapped_column(String(128), comment="社員名")
    department_uuid: Mapped[str | None] = mapped_column(String(64), comment="所属部署UUID")
    user_uuid: Mapped[str | None] = mapped_column(String(64), comment="ログインユーザーUUID")
    email: Mapped[str | None] = mapped_column(String(255), comment="メールアドレス")
    phone: Mapped[str | None] = mapped_column(String(32), comment="電話番号")
    position: Mapped[str | None] = mapped_column(String(128), comment="役職")
    hire_date: Mapped[date | None] = mapped_column(Date, comment="入社日")
    leave_date: Mapped[date | None] = mapped_column(Date, comment="退職日")
