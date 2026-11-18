from __future__ import annotations

from datetime import date

from expression import Result
from hiaok_core.exception import DomainError
from hiaok_core.fp import AsyncResult

from ...domain.entity import Employee
from .base import CrudService
from .datasource import master


class EmployeeService(CrudService[Employee]):
    entity = "Employee"

    @master
    async def transfer(self, org_uuid: str, employee_uuid: str, department_uuid: str) -> Result[Employee, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, employee_uuid))
            .bind(lambda e: e.transfer_to(department_uuid))
            .bind(self.save)
        )

    @master
    async def link_user(self, org_uuid: str, employee_uuid: str, user_uuid: str) -> Result[Employee, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, employee_uuid)).bind(lambda e: e.link_user(user_uuid)).bind(self.save)
        )

    @master
    async def resign(self, org_uuid: str, employee_uuid: str, leave_date: date) -> Result[Employee, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, employee_uuid)).bind(lambda e: e.resign(leave_date)).bind(self.save)
        )
