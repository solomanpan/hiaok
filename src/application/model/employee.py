from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import Employee
from ...domain.vo import Code, Email, PhoneNumber, text_or_none
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class EmployeeModel(EntityModel):
    employee_uuid: str
    employee_no: str
    employee_name: str
    department_uuid: str | None = None
    user_uuid: str | None = None
    email: str | None = None
    phone: str | None = None
    position: str | None = None
    hire_date: date | None = None
    leave_date: date | None = None

    @classmethod
    def from_domain(cls, e: Employee) -> EmployeeModel:
        return cls(
            **entity_fields(e),
            employee_uuid=e.employee_uuid,
            employee_no=e.employee_no.value,
            employee_name=e.employee_name,
            department_uuid=e.department_uuid,
            user_uuid=e.user_uuid,
            email=text_or_none(e.email),
            phone=text_or_none(e.phone),
            position=e.position,
            hire_date=e.hire_date,
            leave_date=e.leave_date,
        )

    def to_domain(self) -> Employee:
        return Employee(
            **entity_kwargs(self),
            employee_uuid=self.employee_uuid,
            employee_no=Code(self.employee_no),
            employee_name=self.employee_name,
            department_uuid=self.department_uuid,
            user_uuid=self.user_uuid,
            email=Email(self.email) if self.email else None,
            phone=PhoneNumber(self.phone) if self.phone else None,
            position=self.position,
            hire_date=self.hire_date,
            leave_date=self.leave_date,
        )


@dataclass(frozen=True, kw_only=True)
class CreateEmployee(CreateMeta):
    org_uuid: str
    employee_no: str
    employee_name: str
    department_uuid: str | None = None
    email: str | None = None
    phone: str | None = None
    position: str | None = None
    hire_date: date | None = None

    def to_domain(self, uuid: str) -> Result[Employee, DomainError]:
        return Employee.hire(
            self.org_uuid,
            uuid,
            self.employee_no,
            self.employee_name,
            department_uuid=self.department_uuid,
            email=self.email,
            phone=self.phone,
            position=self.position,
            hire_date=self.hire_date,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class OnboardEmployee:
    """Hire + (optionally) open a login account in one use case."""

    employee: CreateEmployee
    tenant_uuid: str | None = None
    username: str | None = None
    password: str | None = field(default=None, repr=False)
    role_uuids: tuple[str, ...] = ()

    def to_domain(self, uuid: str, /) -> Result[Employee, DomainError]:
        """The employee part; the optional login account is built by ``OnboardingService``."""
        return self.employee.to_domain(uuid)


@dataclass(frozen=True, kw_only=True)
class UpdateEmployee(UpdateMeta):
    employee_name: str | None = None
    email: str | None = None
    phone: str | None = None
    position: str | None = None

    def apply_to(self, e: Employee) -> Result[Employee, DomainError]:
        return e.update(
            employee_name=self.employee_name, email=self.email, phone=self.phone, position=self.position
        ).map(self.apply_meta)
