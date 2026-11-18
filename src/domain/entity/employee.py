from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from datetime import date
from typing import Any

from expression import Ok, Result, effect
from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog, ErrorSpec

from ..enum import Status
from ..vo import Code, Email, PhoneNumber, non_blank
from .base import AggregateRoot
from .event import EmployeeLinkedToUser, EmployeeTransferred


class EmployeeErrors(ErrorCatalog):
    left = ErrorSpec.validation("employee_left", "cannot transfer an employee who has left")
    already_linked = ErrorSpec.conflict("employee_already_linked", "employee is already linked to user '{user_uuid}'")
    invalid_leave_date = ErrorSpec.validation("invalid_leave_date", "leave_date must be after hire_date")


@dataclass(frozen=True, kw_only=True)
class Employee(AggregateRoot):
    employee_uuid: str
    employee_no: Code
    employee_name: str
    department_uuid: str | None = None
    user_uuid: str | None = None  # optional login account
    email: Email | None = None
    phone: PhoneNumber | None = None
    position: str | None = None
    hire_date: date | None = None
    leave_date: date | None = None

    @property
    def uuid(self) -> str:
        return self.employee_uuid

    @staticmethod
    def hire(
        org_uuid: str,
        employee_uuid: str,
        employee_no: str,
        employee_name: str,
        *,
        department_uuid: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        position: str | None = None,
        hire_date: date | None = None,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Employee, DomainError]:
        @effect.result[Employee, DomainError]()
        def build() -> Generator[Any, Any, Employee]:
            no = yield from Code.create(employee_no, "employee_no")
            name = yield from non_blank(employee_name, "employee_name")
            mail = yield from Email.optional(email)
            tel = yield from PhoneNumber.optional(phone)
            emp = Employee(
                org_uuid=org_uuid,
                employee_uuid=employee_uuid,
                employee_no=no,
                employee_name=name,
                department_uuid=department_uuid,
                email=mail,
                phone=tel,
                position=position,
                hire_date=hire_date,
                description=description,
                remark=remark,
            )
            return emp.created()

        return build()

    def update(
        self,
        *,
        employee_name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        position: str | None = None,
    ) -> Result[Employee, DomainError]:
        @effect.result[Employee, DomainError]()
        def build() -> Generator[Any, Any, Employee]:
            name = (
                (yield from non_blank(employee_name, "employee_name"))
                if employee_name is not None
                else self.employee_name
            )
            mail = (yield from Email.optional(email)) if email is not None else self.email
            tel = (yield from PhoneNumber.optional(phone)) if phone is not None else self.phone
            return self.changed(employee_name=name, email=mail, phone=tel, position=position or self.position)

        return build()

    def transfer_to(self, department_uuid: str) -> Result[Employee, DomainError]:
        if self.leave_date is not None:
            return EmployeeErrors.left.err()
        if department_uuid == self.department_uuid:
            return Ok(self)
        return Ok(
            self.changed(department_uuid=department_uuid).record(
                EmployeeTransferred(
                    org_uuid=self.org_uuid,
                    employee_uuid=self.employee_uuid,
                    from_department_uuid=self.department_uuid,
                    to_department_uuid=department_uuid,
                )
            )
        )

    def link_user(self, user_uuid: str) -> Result[Employee, DomainError]:
        if self.user_uuid == user_uuid:
            return Ok(self)
        if self.user_uuid is not None:
            return EmployeeErrors.already_linked.err(user_uuid=self.user_uuid)
        return Ok(
            self.changed(user_uuid=user_uuid).record(
                EmployeeLinkedToUser(org_uuid=self.org_uuid, employee_uuid=self.employee_uuid, user_uuid=user_uuid)
            )
        )

    def resign(self, leave_date: date) -> Result[Employee, DomainError]:
        if self.hire_date is not None and leave_date < self.hire_date:
            return EmployeeErrors.invalid_leave_date.err()
        return Ok(self.changed(leave_date=leave_date, state=Status.DISABLED))
