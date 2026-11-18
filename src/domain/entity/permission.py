from __future__ import annotations

from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Ok, Result, effect
from hiaok_core.exception import DomainError

from ..enum import PermType
from ..vo import Code, non_blank
from ..vo.text import PERM_CODE
from .base import AggregateRoot


@dataclass(frozen=True, kw_only=True)
class Permission(AggregateRoot):
    """``perm_code`` follows ``resource:action`` (e.g. ``project:create``)."""

    permission_uuid: str
    perm_code: Code
    perm_name: str
    perm_type: PermType = PermType.API
    resource: str | None = None
    action: str | None = None
    menu_uuid: str | None = None

    @property
    def uuid(self) -> str:
        return self.permission_uuid

    @staticmethod
    def create(
        org_uuid: str,
        permission_uuid: str,
        perm_code: str,
        perm_name: str,
        *,
        perm_type: PermType = PermType.API,
        resource: str | None = None,
        action: str | None = None,
        menu_uuid: str | None = None,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[Permission, DomainError]:
        @effect.result[Permission, DomainError]()
        def build() -> Generator[Any, Any, Permission]:
            code = yield from Code.create(perm_code, "perm_code", PERM_CODE)
            name = yield from non_blank(perm_name, "perm_name")
            derived_resource, _, derived_action = code.value.partition(":")
            perm = Permission(
                org_uuid=org_uuid,
                permission_uuid=permission_uuid,
                perm_code=code,
                perm_name=name,
                perm_type=PermType(perm_type),
                resource=resource or derived_resource,
                action=action or derived_action or None,
                menu_uuid=menu_uuid,
                description=description,
                remark=remark,
            )
            return perm.created()

        return build()

    def update(self, *, perm_name: str | None = None, menu_uuid: str | None = None) -> Result[Permission, DomainError]:
        if perm_name is None:
            return Ok(self.changed(menu_uuid=menu_uuid or self.menu_uuid))
        return non_blank(perm_name, "perm_name").map(
            lambda name: self.changed(perm_name=name, menu_uuid=menu_uuid or self.menu_uuid)
        )
