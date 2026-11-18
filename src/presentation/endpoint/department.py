from fastapi import APIRouter, status

from ..dependency import (
    AppointDepartmentHeadDep,
    DepartmentCrudDep,
    DepartmentTreeDep,
    MoveDepartmentDep,
    PageDep,
)
from ..exception import unwrap
from ..schema.common import MoveRequest, PageResponse, TreeNodeResponse
from ..schema.department import (
    AppointHeadRequest,
    DepartmentCreateRequest,
    DepartmentResponse,
    DepartmentUpdateRequest,
)

router = APIRouter(prefix="/orgs/{org_uuid}/departments", tags=["department"])


@router.get("/tree", name="department_tree")
async def department_tree(org_uuid: str, uc: DepartmentTreeDep) -> list[TreeNodeResponse[DepartmentResponse]]:
    return [TreeNodeResponse[DepartmentResponse].of(node, DepartmentResponse.of) for node in await uc(org_uuid)]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department(org_uuid: str, body: DepartmentCreateRequest, uc: DepartmentCrudDep) -> DepartmentResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), DepartmentResponse.of)


@router.get("")
async def list_departments(org_uuid: str, page: PageDep, uc: DepartmentCrudDep) -> PageResponse[DepartmentResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), DepartmentResponse.of)


@router.get("/{department_uuid}")
async def get_department(org_uuid: str, department_uuid: str, uc: DepartmentCrudDep) -> DepartmentResponse:
    return unwrap(await uc.get(org_uuid, department_uuid), DepartmentResponse.of)


@router.patch("/{department_uuid}")
async def update_department(
    org_uuid: str, department_uuid: str, body: DepartmentUpdateRequest, uc: DepartmentCrudDep
) -> DepartmentResponse:
    return unwrap(await uc.update(org_uuid, department_uuid, body.to_command()), DepartmentResponse.of)


@router.delete("/{department_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(org_uuid: str, department_uuid: str, uc: DepartmentCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, department_uuid), lambda _: None)


@router.put("/{department_uuid}/parent")
async def move_department(
    org_uuid: str, department_uuid: str, body: MoveRequest, uc: MoveDepartmentDep
) -> DepartmentResponse:
    """Cycle-safe: moving a node under its own subtree is rejected (422 tree_cycle)."""
    return unwrap(await uc(org_uuid, department_uuid, body.parent_uuid), DepartmentResponse.of)


@router.put("/{department_uuid}/head")
async def appoint_department_head(
    org_uuid: str, department_uuid: str, body: AppointHeadRequest, uc: AppointDepartmentHeadDep
) -> DepartmentResponse:
    """Sets ``department.employee_uuid`` (the head); the employee must exist and be active."""
    return unwrap(await uc(org_uuid, department_uuid, body.employee_uuid), DepartmentResponse.of)
