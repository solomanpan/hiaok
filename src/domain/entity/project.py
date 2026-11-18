from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Result, effect
from hiaok_core.exception import DomainError

from ..vo import Code, non_blank
from .base import AggregateRoot


@dataclass(frozen=True, kw_only=True)
class Project(AggregateRoot):
    project_uuid: str
    tenant_uuid: str
    project_code: Code
    project_name: str
    owner_user_uuid: str | None = None

    @property
    def uuid(self) -> str:
        return self.project_uuid

    @staticmethod
    def create(
        org_uuid: str,
        project_uuid: str,
        tenant_uuid: str,
        project_code: str,
        project_name: str,
        *,
        owner_user_uuid: str | None = None,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Project, DomainError]:
        @effect.result[Project, DomainError]()
        def build() -> Generator[Any, Any, Project]:
            code = yield from Code.create(project_code, "project_code")
            name = yield from non_blank(project_name, "project_name")
            project = Project(
                org_uuid=org_uuid,
                project_uuid=project_uuid,
                tenant_uuid=tenant_uuid,
                project_code=code,
                project_name=name,
                owner_user_uuid=owner_user_uuid,
                description=description,
                remark=remark,
            )
            return project.created()

        return build()

    def update(
        self, *, project_name: str | None = None, owner_user_uuid: str | None = None
    ) -> Result[Project, DomainError]:
        @effect.result[Project, DomainError]()
        def build() -> Generator[Any, Any, Project]:
            name = (
                (yield from non_blank(project_name, "project_name")) if project_name is not None else self.project_name
            )
            return self.changed(project_name=name, owner_user_uuid=owner_user_uuid or self.owner_user_uuid)

        return build()
