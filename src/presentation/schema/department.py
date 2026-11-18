from __future__ import annotations

from pydantic import BaseModel, Field

from ...application.model import CreateDepartment, DepartmentModel, UpdateDepartment
from .common import EntityResponse, MetaRequest, MetaUpdateRequest


class DepartmentCreateRequest(MetaRequest):
    department_code: str
    department_name: str
    parent_department_uuid: str | None = None
    sort_order: int = Field(default=0, ge=0)

    def to_command(self, org_uuid: str) -> CreateDepartment:
        return CreateDepartment(org_uuid=org_uuid, **self.model_dump())


class DepartmentUpdateRequest(MetaUpdateRequest):
    department_name: str | None = None
    sort_order: int | None = Field(default=None, ge=0)

    def to_command(self) -> UpdateDepartment:
        return UpdateDepartment(**self.model_dump())


class AppointHeadRequest(BaseModel):
    employee_uuid: str | None = Field(default=None, description="null = clear the department head")


class DepartmentResponse(EntityResponse):
    department_uuid: str
    department_code: str
    department_name: str
    parent_department_uuid: str | None = None
    employee_uuid: str | None = Field(default=None, description="department head")
    sort_order: int

    @classmethod
    def of(cls, m: DepartmentModel) -> DepartmentResponse:
        return cls.model_validate(m)
