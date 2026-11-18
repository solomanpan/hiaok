from __future__ import annotations

from datetime import date

from pydantic import EmailStr, Field

from ...application.model import CreateEmployee, EmployeeModel, OnboardEmployee, UpdateEmployee
from .common import ApiModel, EntityResponse, Keyed, MetaRequest, MetaUpdateRequest, OrgScoped
from .user import UserResponse


class AccountRequest(ApiModel):
    """Optional: open a login user for the new employee in the same transaction."""

    tenant_uuid: str
    username: str
    password: str = Field(..., min_length=8, repr=False)
    role_uuids: list[str] = Field(default_factory=list)


class EmployeeOnboardRequest(OrgScoped, MetaRequest):
    employee_no: str = Field(..., examples=["E0001"])
    employee_name: str
    department_uuid: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    position: str | None = None
    hire_date: date | None = None
    account: AccountRequest | None = None

    def to_command(self) -> OnboardEmployee:
        employee = CreateEmployee(**self.model_dump(exclude={"account"}))
        if self.account is None:
            return OnboardEmployee(employee=employee)
        return OnboardEmployee(
            employee=employee,
            tenant_uuid=self.account.tenant_uuid,
            username=self.account.username,
            password=self.account.password,
            role_uuids=tuple(self.account.role_uuids),
        )


class EmployeeUpdateRequest(Keyed, MetaUpdateRequest):
    employee_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    position: str | None = None

    def to_command(self) -> UpdateEmployee:
        return UpdateEmployee(**self.patch())


class TransferRequest(Keyed):
    department_uuid: str


class ResignRequest(Keyed):
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


class OnboardResponse(ApiModel):
    employee: EmployeeResponse
    user: UserResponse | None = None
