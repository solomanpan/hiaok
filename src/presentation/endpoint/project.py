from fastapi import APIRouter

from ..dependency import ProjectCrudDep, WriteSubmitterDep, has_permission
from ..schema.command import AcceptedResponse, accepted
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, reply
from ..schema.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest

router = APIRouter(prefix="/project", tags=["project"])


@router.post("/add", dependencies=[has_permission("project:add")])
async def create_project(
    request: ApiRequest[ProjectCreateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.create("Project", request.request_id, info.org_uuid, info.to_command()))


@router.post("/list", dependencies=[has_permission("project:list")])
async def list_projects(
    request: ApiRequest[OrgPageRequest], usecase: ProjectCrudDep
) -> ApiResponse[PageResponse[ProjectResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usecase.list(info.org_uuid, info.query), ProjectResponse.of))


@router.post("/get", dependencies=[has_permission("project:get")])
async def get_project(request: ApiRequest[Keyed], usecase: ProjectCrudDep) -> ApiResponse[ProjectResponse]:
    info = request.req_info
    return reply(await usecase.get(info.org_uuid, info.uuid), ProjectResponse.of)


@router.post("/update", dependencies=[has_permission("project:update")])
async def update_project(
    request: ApiRequest[ProjectUpdateRequest], submitter: WriteSubmitterDep
) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.update("Project", request.request_id, info.org_uuid, info.uuid, info.to_command()))


@router.post("/delete", dependencies=[has_permission("project:delete")])
async def delete_project(request: ApiRequest[Keyed], submitter: WriteSubmitterDep) -> ApiResponse[AcceptedResponse]:
    info = request.req_info
    return accepted(await submitter.delete("Project", request.request_id, info.org_uuid, info.uuid))
