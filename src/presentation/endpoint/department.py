from fastapi import APIRouter

from ...application.model import AppointHeadPayload, MovePayload
from ..dependency import DepartmentCrudDep, DepartmentTreeDep, WriteSubmitterDep
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, MoveRequest, OrgPageRequest, OrgScoped, PageResponse, TreeNodeResponse
from ..schema.department import AppointHeadRequest, DepartmentCreateRequest, DepartmentResponse, DepartmentUpdateRequest
from ..schema.envelope import ApiRequest, ApiResponse, reply

router = APIRouter(prefix="/department", tags=["department"])


@router.post("/tree")
async def department_tree(
    request: ApiRequest[OrgScoped], usecase: DepartmentTreeDep
) -> ApiResponse[list[TreeNodeResponse[DepartmentResponse]]]:
    nodes = await usecase(request.req_info.org_uuid)
    return ApiResponse.ok([TreeNodeResponse[DepartmentResponse].of(node, DepartmentResponse.of) for node in nodes])


@router.post("/add")
async def create_department(
    request: ApiRequest[DepartmentCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Department", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list")
async def list_departments(
    request: ApiRequest[OrgPageRequest], usecase: DepartmentCrudDep
) -> ApiResponse[PageResponse[DepartmentResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), DepartmentResponse.of))


@router.post("/get")
async def get_department(request: ApiRequest[Keyed], usecase: DepartmentCrudDep) -> ApiResponse[DepartmentResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), DepartmentResponse.of)


@router.post("/update")
async def update_department(
    request: ApiRequest[DepartmentUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(
        await submitter.update("Department", request.request_id, info.org_uuid, info.uuid, info.to_command())
    )


@router.post("/delete")
async def delete_department(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("Department", request.request_id, info.org_uuid, info.uuid))


@router.post("/move")
async def move_department(
    request: ApiRequest[MoveRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    """Cycle-safe: moving a node under its own subtree fails with ``tree_cycle``."""
    info = request.req_info
    return accepted(
        await submitter.act(
            "Department", "move", request.request_id, info.org_uuid, info.uuid, MovePayload(info.parent_uuid)
        )
    )


@router.post("/appoint-head")
async def appoint_department_head(
    request: ApiRequest[AppointHeadRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    """Sets ``department.employee_uuid`` (the head); the employee must exist and be active."""
    info = request.req_info
    return accepted(
        await submitter.act(
            "Department",
            "appoint_head",
            request.request_id,
            info.org_uuid,
            info.uuid,
            AppointHeadPayload(info.employee_uuid),
        )
    )
