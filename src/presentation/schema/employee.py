from __future__ import annotations

from datetime import date

from pydantic import BaseModel, EmailStr, Field

from ...application.model import CreateEmployee, EmployeeModel, OnboardEmployee, UpdateEmployee
from .common import EntityResponse, MetaRequest, MetaUpdateRequest
from .user import UserResponse


class AccountRequest(BaseModel):
    """Optional: open a login user for the new employee in the same transaction."""

    tenant_uuid: str
    username: str
    password: str = Field(..., min_length=8, repr=False)
    role_uuids: list[str] = Field(default_factory=list)


class EmployeeOnboardRequest(MetaRequest):
    employee_no: str = Field(..., examples=["E0001"])
    employee_name: str
    department_uuid: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    position: str | None = None
    hire_date: date | None = None
    account: AccountRequest | None = None

    def to_command(self, org_uuid: str) -> OnboardEmployee:
        employee = CreateEmployee(org_uuid=org_uuid, **self.model_dump(exclude={"account"}))
        if self.account is None:
            return OnboardEmployee(employee=employee)
        return OnboardEmployee(
            employee=employee,
            tenant_uuid=self.account.tenant_uuid,
            username=self.account.username,
            password=self.account.password,
            role_uuids=tuple(self.account.role_uuids),
        )


class EmployeeUpdateRequest(MetaUpdateRequest):
    employee_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    position: str | None = None

    def to_command(self) -> UpdateEmployee:
        return UpdateEmployee(**self.model_dump())


class TransferRequest(BaseModel):
    department_uuid: str


class ResignRequest(BaseModel):
    leave_date: date


class EmployeeResponse(EntityResponse):
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
    def of(cls, m: EmployeeModel) -> EmployeeResponse:
        return cls.model_validate(m)


class OnboardResponse(BaseModel):
    employee: EmployeeResponse
    user: UserResponse | None = None
