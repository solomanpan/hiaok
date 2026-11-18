from fastapi import APIRouter, status

from ..dependency import PageDep, ProjectCrudDep
from ..exception import unwrap
from ..schema.common import PageResponse
from ..schema.project import ProjectCreateRequest, ProjectResponse, ProjectUpdateRequest

router = APIRouter(prefix="/orgs/{org_uuid}/projects", tags=["project"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(org_uuid: str, body: ProjectCreateRequest, uc: ProjectCrudDep) -> ProjectResponse:
    return unwrap(await uc.create(body.to_command(org_uuid)), ProjectResponse.of)


@router.get("")
async def list_projects(org_uuid: str, page: PageDep, uc: ProjectCrudDep) -> PageResponse[ProjectResponse]:
    return PageResponse.of(await uc.list(org_uuid, page), ProjectResponse.of)


@router.get("/{project_uuid}")
async def get_project(org_uuid: str, project_uuid: str, uc: ProjectCrudDep) -> ProjectResponse:
    return unwrap(await uc.get(org_uuid, project_uuid), ProjectResponse.of)


@router.patch("/{project_uuid}")
async def update_project(
    org_uuid: str, project_uuid: str, body: ProjectUpdateRequest, uc: ProjectCrudDep
) -> ProjectResponse:
    return unwrap(await uc.update(org_uuid, project_uuid, body.to_command()), ProjectResponse.of)


@router.delete("/{project_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(org_uuid: str, project_uuid: str, uc: ProjectCrudDep) -> None:
    unwrap(await uc.delete(org_uuid, project_uuid), lambda _: None)
