from fastapi import APIRouter, status

from ..dependency import (
    EmployeeCrudDep,
    OnboardEmployeeDep,
    PageDep,
    ResignEmployeeDep,
    TransferEmployeeDep,
)
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.employee import (
    EmployeeOnboardRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
    OnboardResponse,
    ResignRequest,
    TransferRequest,
)
from ..schema.user import UserResponse

router = APIRouter(prefix="/orgs/{org_uuid}/employees", tags=["employee"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def onboard_employee(org_uuid: str, body: EmployeeOnboardRequest, uc: OnboardEmployeeDep) -> OnboardResponse:
    """Hire, and when ``account`` is given also register + link a login user - one transaction."""
    return unwrap(
        await uc(body.to_command(org_uuid)),
        lambda pair: OnboardResponse(
            employee=EmployeeResponse.of(pair[0]), user=None if pair[1] is None else UserResponse.of(pair[1])
        ),
    )


@router.get("")
async def list_employees(org_uuid: str, page: PageDep, uc: EmployeeCrudDep) -> PageResponse[EmployeeResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), EmployeeResponse.of)


@router.get("/{employee_uuid}")
async def get_employee(org_uuid: str, employee_uuid: str, uc: EmployeeCrudDep) -> EmployeeResponse:
    return unwrap(await uc.get(org_uuid, employee_uuid), EmployeeResponse.of)


@router.patch("/{employee_uuid}")
async def update_employee(
    org_uuid: str, employee_uuid: str, body: EmployeeUpdateRequest, uc: EmployeeCrudDep
) -> EmployeeResponse:
    return unwrap(await uc.update(org_uuid, employee_uuid, body.to_command()), EmployeeResponse.of)


@router.delete("/{employee_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_employee(org_uuid: str, employee_uuid: str, uc: EmployeeCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, employee_uuid), lambda _: None)


@router.post("/{employee_uuid}/transfer")
async def transfer_employee(
    org_uuid: str, employee_uuid: str, body: TransferRequest, uc: TransferEmployeeDep
) -> EmployeeResponse:
    return unwrap(await uc(org_uuid, employee_uuid, body.department_uuid), EmployeeResponse.of)


@router.post("/{employee_uuid}/resign")
async def resign_employee(
    org_uuid: str, employee_uuid: str, body: ResignRequest, uc: ResignEmployeeDep
) -> EmployeeResponse:
    return unwrap(await uc(org_uuid, employee_uuid, body.leave_date), EmployeeResponse.of)
