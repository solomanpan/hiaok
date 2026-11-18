from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Ok, Result, effect
from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog, ErrorSpec

from ..vo import Code, non_blank
from .base import AggregateRoot


class UserGroupErrors(ErrorCatalog):
    invalid_parent = ErrorSpec.validation("invalid_parent", "a group cannot be its own parent")


@dataclass(frozen=True, kw_only=True)
class UserGroup(AggregateRoot):
    group_uuid: str
    tenant_uuid: str
    group_code: Code
    group_name: str
    parent_group_uuid: str | None = None
    sort_order: int = 0

    @property
    def uuid(self) -> str:
        return self.group_uuid

    @staticmethod
    def create(
        org_uuid: str,
        group_uuid: str,
        tenant_uuid: str,
        group_code: str,
        group_name: str,
        *,
        parent_group_uuid: str | None = None,
        sort_order: int = 0,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[UserGroup, DomainError]:
        @effect.result[UserGroup, DomainError]()
        def build() -> Generator[Any, Any, UserGroup]:
            code = yield from Code.create(group_code, "group_code")
            name = yield from non_blank(group_name, "group_name")
            group = UserGroup(
                org_uuid=org_uuid,
                group_uuid=group_uuid,
                tenant_uuid=tenant_uuid,
                group_code=code,
                group_name=name,
                parent_group_uuid=parent_group_uuid,
                sort_order=sort_order,
                description=description,
                remark=remark,
            )
            return group.created()

        return build()

    def update(self, *, group_name: str | None = None, sort_order: int | None = None) -> Result[UserGroup, DomainError]:
        @effect.result[UserGroup, DomainError]()
        def build() -> Generator[Any, Any, UserGroup]:
            name = (yield from non_blank(group_name, "group_name")) if group_name is not None else self.group_name
            return self.changed(group_name=name, sort_order=self.sort_order if sort_order is None else sort_order)

        return build()

    def move_to(self, parent_group_uuid: str | None) -> Result[UserGroup, DomainError]:
        if parent_group_uuid == self.group_uuid:
            return UserGroupErrors.invalid_parent.err()
        return Ok(self.changed(parent_group_uuid=parent_group_uuid))
