from fastapi import APIRouter

from ..dependency import ProjectCrudDep
from ..schema.common import Keyed, OrgPageRequest, PageResponse
from ..schema.envelope import ApiRequest, ApiResponse, done, reply
from ..schema.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest

router = APIRouter(prefix="/project", tags=["project"])


@router.post("/add")
async def create_project(
    request: ApiRequest[ProjectCreateRequest], usercase: ProjectCrudDep
) -> ApiResponse[ProjectResponse]:
    return reply(await usercase.create(request.req_info.to_command()), ProjectResponse.of)


@router.post("/list")
async def list_projects(
    request: ApiRequest[OrgPageRequest], usercase: ProjectCrudDep
) -> ApiResponse[PageResponse[ProjectResponse]]:
    info = request.req_info
    return ApiResponse.ok(PageResponse.of(await usercase.list(info.org_uuid, info.query), ProjectResponse.of))


@router.post("/get")
async def get_project(request: ApiRequest[Keyed], usercase: ProjectCrudDep) -> ApiResponse[ProjectResponse]:
    info = request.req_info
    return reply(await usercase.get(info.org_uuid, info.uuid), ProjectResponse.of)


@router.post("/update")
async def update_project(
    request: ApiRequest[ProjectUpdateRequest], usercase: ProjectCrudDep
) -> ApiResponse[ProjectResponse]:
    info = request.req_info
    return reply(await usercase.update(info.org_uuid, info.uuid, info.to_command()), ProjectResponse.of)


@router.post("/delete")
async def delete_project(request: ApiRequest[Keyed], usercase: ProjectCrudDep) -> ApiResponse[None]:
    info = request.req_info
    return done(await usercase.delete(info.org_uuid, info.uuid))
