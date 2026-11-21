from fastapi import APIRouter

from ...application.model import ResignPayload, TransferPayload
from ..dependency import EmployeeCrudDep, OnboardEmployeeDep, WriteSubmitterDep, has_permission
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.employee import (
    EmployeeOnboardRequest,
    EmployeeResponse,
    EmployeeUpdateRequest,
    OnboardResponse,
    ResignRequest,
    TransferRequest,
)
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.user import UserResponse

router = APIRouter(prefix="/employee", tags=["employee"])


@router.post("/add", dependencies=[has_permission("employee:add")])
async def onboard_employee(
    request: ApiRequest[EmployeeOnboardRequest], usecase: OnboardEmployeeDep
) -> ApiResponse[OnboardResponse]:
    """Synchronous: ``account.password`` is clear text and must not be written to a Kafka topic.

    Hire, and when ``account`` is given also register + link a login user - one transaction."""
    return reply(
        await usecase(request.req_info.to_command()),
        lambda pair: OnboardResponse(
            employee=EmployeeResponse.of(pair[0]), user=None if pair[1] is None else UserResponse.of(pair[1])
        ),
    )


@router.post("/list", dependencies=[has_permission("employee:list")])
async def list_employees(
    request: ApiRequest[OrgPageRequest], usecase: EmployeeCrudDep
) -> ApiResponse[PageResponse[EmployeeResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), EmployeeResponse.of))


@router.post("/get", dependencies=[has_permission("employee:get")])
async def get_employee(request: ApiRequest[Keyed], usecase: EmployeeCrudDep) -> ApiResponse[EmployeeResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), EmployeeResponse.of)


@router.post("/update", dependencies=[has_permission("employee:update")])
async def update_employee(
    request: ApiRequest[EmployeeUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.update("Employee", request.request_id, info.org_uuid, info.uuid, info.to_command()))


@router.post("/delete", dependencies=[has_permission("employee:delete")])
async def delete_employee(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("Employee", request.request_id, info.org_uuid, info.uuid))


@router.post("/transfer", dependencies=[has_permission("employee:transfer")])
async def transfer_employee(
    request: ApiRequest[TransferRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    payload = TransferPayload(info.department_uuid)
    return accepted(await submitter.act("Employee", "transfer", request.request_id, info.org_uuid, info.uuid, payload))


@router.post("/resign", dependencies=[has_permission("employee:resign")])
async def resign_employee(
    request: ApiRequest[ResignRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    payload = ResignPayload(info.leave_date)
    return accepted(await submitter.act("Employee", "resign", request.request_id, info.org_uuid, info.uuid, payload))
