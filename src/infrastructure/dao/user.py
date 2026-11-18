"""``user`` (root) + ``user_detail`` (1:1 entity) + ``user_role`` (link table)."""

from __future__ import annotations

from collections.abc import Iterable

from ...domain.entity import User, UserDetail
from ...domain.vo import Email, PasswordHash, PhoneNumber, RoleAssignment, Username, text_or_none
from ..database import RoutingDatabase
from ..do import UserDetailDO, UserDO, UserRoleDO
from .base import EntityDao, LinkDao, entity_kwargs


class UserDetailDao(EntityDao[UserDetailDO, UserDetail]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, UserDetailDO, "user_uuid")

    def to_entity(self, do: UserDetailDO) -> UserDetail:
        return UserDetail(
            **entity_kwargs(do),
            user_uuid=do.user_uuid,
            nickname=do.nickname,
            real_name=do.real_name,
            avatar_url=do.avatar_url,
            gender=do.gender,
            birthday=do.birthday,
            locale=do.locale,
            timezone=do.timezone,
        )

    def to_do(self, entity: UserDetail, do: UserDetailDO | None = None) -> UserDetailDO:
        target = self.new_or(do, entity)
        target.user_uuid = entity.user_uuid
        target.nickname = entity.nickname
        target.real_name = entity.real_name
        target.avatar_url = entity.avatar_url
        target.gender = entity.gender
        target.birthday = entity.birthday
        target.locale = entity.locale
        target.timezone = entity.timezone
        return target


class UserDao(EntityDao[UserDO, User]):
    def __init__(self, db: RoutingDatabase, details: UserDetailDao | None = None) -> None:
        super().__init__(db, UserDO, "user_uuid")
        self._details = details or UserDetailDao(db)

    async def find_by_username(self, org_uuid: str, tenant_uuid: str, username: str) -> UserDO | None:
        return await self.find_one(org_uuid, tenant_uuid=tenant_uuid, username=username)

    def to_entity(
        self,
        do: UserDO,
        *,
        detail: UserDetailDO | None = None,
        roles: Iterable[UserRoleDO] = (),
    ) -> User:
        return User(
            **entity_kwargs(do),
            user_uuid=do.user_uuid,
            tenant_uuid=do.tenant_uuid,
            username=Username(do.username),
            password_hash=PasswordHash(do.password_hash),
            email=Email(do.email) if do.email else None,
            phone=PhoneNumber(do.phone) if do.phone else None,
            group_uuid=do.group_uuid,
            last_login_time=do.last_login_time,
            detail=self._details.to_entity(detail) if detail else UserDetail.empty(do.org_uuid, do.user_uuid),
            roles=frozenset(RoleAssignment(r.role_uuid, r.project_uuid) for r in roles),
        )

    def to_do(self, entity: User, do: UserDO | None = None) -> UserDO:
        """Root row only; ``user_detail`` / ``user_role`` are written by their own DAOs."""
        target = self.new_or(do, entity)
        target.user_uuid = entity.user_uuid
        target.tenant_uuid = entity.tenant_uuid
        target.username = entity.username.value
        target.password_hash = entity.password_hash.value
        target.email = text_or_none(entity.email)
        target.phone = text_or_none(entity.phone)
        target.group_uuid = entity.group_uuid
        target.last_login_time = entity.last_login_time
        return target


class UserRoleDao(LinkDao[UserRoleDO]):
    def __init__(self, db: RoutingDatabase) -> None:
        super().__init__(db, UserRoleDO, "user_uuid")
