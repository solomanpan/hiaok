from __future__ import annotations

from dataclasses import dataclass

from .base import ValueObject

TENANT_WIDE = ""


@dataclass(frozen=True, order=True)
class RoleAssignment(ValueObject):
    """A row of ``user_role``: role granted tenant-wide (``project_uuid == ""``) or inside one project."""

    role_uuid: str
    project_uuid: str = TENANT_WIDE

    @property
    def tenant_wide(self) -> bool:
        return self.project_uuid == TENANT_WIDE
