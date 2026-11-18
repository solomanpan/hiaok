from fastapi import APIRouter

from ..dependency import (
    EmployeeCrudDep,
    OnboardEmployeeDep,
    ResignEmployeeDep,
    TransferEmployeeDep,
)
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.employee import (
    EmployeeOnboardRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
    OnboardResponse,
    ResignRequest,
    TransferRequest,
)
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.user import UserResponse

router = APIRouter(prefix="/employee", tags=["employee"])


@router.post("/add")
async def onboard_employee(
    request: ApiRequest[EmployeeOnboardRequest], usercase: OnboardEmployeeDep
) -> ApiResponse[OnboardResponse]:
    """Hire, and when ``account`` is given also register + link a login user - one transaction."""
    return reply(
        await usercase(request.req_info.to_command()),
        lambda pair: OnboardResponse(
            employee=EmployeeResponse.of(pair[0]), user=None if pair[1] is None else UserResponse.of(pair[1])
        ),
    )


@router.post("/list")
async def list_employees(
    request: ApiRequest[OrgPageRequest], usercase: EmployeeCrudDep
) -> ApiResponse[PageResponse[EmployeeResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), EmployeeResponse.of))


@router.post("/get")
async def get_employee(request: ApiRequest[Keyed], usercase: EmployeeCrudDep) -> ApiResponse[EmployeeResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), EmployeeResponse.of)


@router.post("/update")
async def update_employee(
    request: ApiRequest[EmployeeUpdateRequest], usercase: EmployeeCrudDep
) -> ApiResponse[EmployeeResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), EmployeeResponse.of)


@router.post("/delete")
async def delete_employee(request: ApiRequest[Keyed], usercase: EmployeeCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))


@router.post("/transfer")
async def transfer_employee(
    request: ApiRequest[TransferRequest], usercase: TransferEmployeeDep
) -> ApiResponse[EmployeeResponse]:
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.uuid, info.department_uuid), EmployeeResponse.of)


@router.post("/resign")
async def resign_employee(
    request: ApiRequest[ResignRequest], usercase: ResignEmployeeDep
) -> ApiResponse[EmployeeResponse]:
    info = request.req_info
    return reply(await usercase(info.org_uuid, info.uuid, info.leave_date), EmployeeResponse.of)
