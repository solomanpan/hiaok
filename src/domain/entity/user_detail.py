from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from .base import Entity


@dataclass(frozen=True, kw_only=True)
class UserDetail(Entity):
    """``user_detail`` (1:1 with User, identity = user_uuid). Lives inside the User aggregate."""

    user_uuid: str
    nickname: str | None = None
    real_name: str | None = None
    avatar_url: str | None = None
    gender: str | None = None
    birthday: date | None = None
    locale: str | None = None
    timezone: str | None = None

    @staticmethod
    def empty(org_uuid: str, user_uuid: str) -> UserDetail:
        return UserDetail(org_uuid=org_uuid, user_uuid=user_uuid)
