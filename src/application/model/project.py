from __future__ import annotations

from dataclasses import dataclass

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import Project
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class ProjectModel(EntityModel):
    project_uuid: str
    tenant_uuid: str
    project_code: str
    project_name: str
    owner_user_uuid: str | None = None

    @classmethod
    def from_domain(cls, p: Project) -> ProjectModel:
        return cls(
            **entity_fields(p),
            project_uuid=p.project_uuid,
            tenant_uuid=p.tenant_uuid,
            project_code=p.project_code.value,
            project_name=p.project_name,
            owner_user_uuid=p.owner_user_uuid,
        )

    def to_domain(self) -> Project:
        return Project(
            **entity_kwargs(self),
            project_uuid=self.project_uuid,
            tenant_uuid=self.tenant_uuid,
            project_code=Code(self.project_code),
            project_name=self.project_name,
            owner_user_uuid=self.owner_user_uuid,
        )


@dataclass(frozen=True, kw_only=True)
class CreateProject(CreateMeta):
    org_uuid: str
    tenant_uuid: str
    project_code: str
    project_name: str
    owner_user_uuid: str | None = None

    def to_domain(self, uuid: str) -> Result[Project, DomainError]:
        return Project.create(
            self.org_uuid,
            uuid,
            self.tenant_uuid,
            self.project_code,
            self.project_name,
            owner_user_uuid=self.owner_user_uuid,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateProject(UpdateMeta):
    project_name: str | None = None
    owner_user_uuid: str | None = None

    def apply_to(self, p: Project) -> Result[Project, DomainError]:
        return p.update(project_name=self.project_name, owner_user_uuid=self.owner_user_uuid).map(self.apply_meta)
