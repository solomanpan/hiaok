from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Error, Ok, Result, effect
from hiaok_core.exception import DomainError, validation

from ..vo import Code, non_blank
from .base import AggregateRoot
from .event import DepartmentHeadAppointed


@dataclass(frozen=True, kw_only=True)
class Department(AggregateRoot):
    """Org chart node. ``employee_uuid`` = department head (部門責任者)."""

    department_uuid: str
    department_code: Code
    department_name: str
    parent_department_uuid: str | None = None
    employee_uuid: str | None = None
    sort_order: int = 0

    @property
    def uuid(self) -> str:
        return self.department_uuid

    @staticmethod
    def create(
        org_uuid: str,
        department_uuid: str,
        department_code: str,
        department_name: str,
        *,
        parent_department_uuid: str | None = None,
        sort_order: int = 0,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Department, DomainError]:
        @effect.result[Department, DomainError]()
        def build() -> Generator[Any, Any, Department]:
            code = yield from Code.create(department_code, "department_code")
            name = yield from non_blank(department_name, "department_name")
            dept = Department(
                org_uuid=org_uuid,
                department_uuid=department_uuid,
                department_code=code,
                department_name=name,
                parent_department_uuid=parent_department_uuid,
                sort_order=sort_order,
                description=description,
                remark=remark,
            )
            return dept.created()

        return build()

    def update(
        self, *, department_name: str | None = None, sort_order: int | None = None
    ) -> Result[Department, DomainError]:
        @effect.result[Department, DomainError]()
        def build() -> Generator[Any, Any, Department]:
            name = (
                (yield from non_blank(department_name, "department_name"))
                if department_name is not None
                else self.department_name
            )
            return self.changed(department_name=name, sort_order=self.sort_order if sort_order is None else sort_order)

        return build()

    def appoint_head(self, employee_uuid: str | None) -> Department:
        if employee_uuid == self.employee_uuid:
            return self
        return self.changed(employee_uuid=employee_uuid).record(
            DepartmentHeadAppointed(
                org_uuid=self.org_uuid, department_uuid=self.department_uuid, employee_uuid=employee_uuid
            )
        )

    def move_to(self, parent_department_uuid: str | None) -> Result[Department, DomainError]:
        if parent_department_uuid == self.department_uuid:
            return Error(validation("invalid_parent", "a department cannot be its own parent"))
        return Ok(self.changed(parent_department_uuid=parent_department_uuid))
