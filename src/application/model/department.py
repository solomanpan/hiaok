from __future__ import annotations

from dataclasses import dataclass

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import Department
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class DepartmentModel(EntityModel):
    department_uuid: str
    department_code: str
    department_name: str
    parent_department_uuid: str | None = None
    employee_uuid: str | None = None  # department head
    sort_order: int = 0

    @classmethod
    def from_domain(cls, d: Department) -> DepartmentModel:
        return cls(
            **entity_fields(d),
            department_uuid=d.department_uuid,
            department_code=d.department_code.value,
            department_name=d.department_name,
            parent_department_uuid=d.parent_department_uuid,
            employee_uuid=d.employee_uuid,
            sort_order=d.sort_order,
        )

    def to_domain(self) -> Department:
        return Department(
            **entity_kwargs(self),
            department_uuid=self.department_uuid,
            department_code=Code(self.department_code),
            department_name=self.department_name,
            parent_department_uuid=self.parent_department_uuid,
            employee_uuid=self.employee_uuid,
            sort_order=self.sort_order,
        )


@dataclass(frozen=True, kw_only=True)
class CreateDepartment(CreateMeta):
    org_uuid: str
    department_code: str
    department_name: str
    parent_department_uuid: str | None = None
    sort_order: int = 0

    def to_domain(self, uuid: str) -> Result[Department, DomainError]:
        return Department.create(
            self.org_uuid,
            uuid,
            self.department_code,
            self.department_name,
            parent_department_uuid=self.parent_department_uuid,
            sort_order=self.sort_order,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateDepartment(UpdateMeta):
    department_name: str | None = None
    sort_order: int | None = None

    def apply_to(self, d: Department) -> Result[Department, DomainError]:
        return d.update(department_name=self.department_name, sort_order=self.sort_order).map(self.apply_meta)
