from fastapi import APIRouter

from ..dependency import AppointDepartmentHeadDep, DepartmentCrudDep, DepartmentTreeDep, MoveDepartmentDep
from ..schema.common import Keyed, MoveRequest, OrgPageRequest, OrgScoped, PageResponse, TreeNodeResponse
from ..schema.department import AppointHeadRequest, DepartmentCreateRequest, DepartmentResponse, DepartmentUpdateRequest
from ..schema.envelope import ApiRequest, ApiResponse, done, reply

router = APIRouter(prefix="/department", tags=["department"])


@router.post("/tree")
async def department_tree(
    request: ApiRequest[OrgScoped], usercase: DepartmentTreeDep
) -> ApiResponse[list[TreeNodeResponse[DepartmentResponse]]]:
    nodes = await usercase(request.req_info.org_uuid)
    return ApiResponse.ok([TreeNodeResponse[DepartmentResponse].of(node, DepartmentResponse.of) for node in nodes])


@router.post("/add")
async def create_department(
    body: ApiRequest[DepartmentCreateRequest], uc: DepartmentCrudDep
) -> ApiResponse[DepartmentResponse]:
    return reply(await uc.create(body.req_info.to_command()), DepartmentResponse.of)


@router.post("/list")
async def list_departments(
    body: ApiRequest[OrgPageRequest], uc: DepartmentCrudDep
) -> ApiResponse[PageResponse[DepartmentResponse]]:
    info = body.req_info
    return ApiResponse.ok(PageResponse.of(await uc.list(info.org_uuid, info.query), DepartmentResponse.of))


@router.post("/get")
async def get_department(body: ApiRequest[Keyed], uc: DepartmentCrudDep) -> ApiResponse[DepartmentResponse]:
    info = body.req_info
    return reply(await uc.get(info.org_uuid, info.uuid), DepartmentResponse.of)


@router.post("/update")
async def update_department(
    body: ApiRequest[DepartmentUpdateRequest], uc: DepartmentCrudDep
) -> ApiResponse[DepartmentResponse]:
    info = body.req_info
    return reply(await uc.update(info.org_uuid, info.uuid, info.to_command()), DepartmentResponse.of)


@router.post("/delete")
async def delete_department(body: ApiRequest[Keyed], uc: DepartmentCrudDep) -> ApiResponse[None]:
    info = body.req_info
    return done(await uc.delete(info.org_uuid, info.uuid))


@router.post("/move")
async def move_department(body: ApiRequest[MoveRequest], uc: MoveDepartmentDep) -> ApiResponse[DepartmentResponse]:
    """Cycle-safe: moving a node under its own subtree is rejected (``tree_cycle``)."""
    info = body.req_info
    return reply(await uc(info.org_uuid, info.uuid, info.parent_uuid), DepartmentResponse.of)


@router.post("/appoint-head")
async def appoint_department_head(
    body: ApiRequest[AppointHeadRequest], uc: AppointDepartmentHeadDep
) -> ApiResponse[DepartmentResponse]:
    """Sets ``department.employee_uuid`` (the head); the employee must exist and be active."""
    info = body.req_info
    return reply(await uc(info.org_uuid, info.uuid, info.employee_uuid), DepartmentResponse.of)
