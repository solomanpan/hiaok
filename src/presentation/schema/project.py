from __future__ import annotations

from ...application.model import CreateProject, ProjectModel, UpdateProject
from .common import EntityResponse, MetaRequest, MetaUpdateRequest


class ProjectCreateRequest(MetaRequest):
    tenant_uuid: str
    project_code: str
    project_name: str
    owner_user_uuid: str | None = None

    def to_command(self, org_uuid: str) -> CreateProject:
        return CreateProject(org_uuid=org_uuid, **self.model_dump())


class ProjectUpdateRequest(MetaUpdateRequest):
    project_name: str | None = None
    owner_user_uuid: str | None = None

    def to_command(self) -> UpdateProject:
        return UpdateProject(**self.model_dump())


class ProjectResponse(EntityResponse):
    project_uuid: str
    tenant_uuid: str
    project_code: str
    project_name: str
    owner_user_uuid: str | None = None

    @classmethod
    def of(cls, m: ProjectModel) -> ProjectResponse:
        return cls.model_validate(m)
