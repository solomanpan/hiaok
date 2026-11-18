from __future__ import annotations

from expression import Option, Some, option
from toolz import groupby

from ...domain.entity import User
from ..dao import UserDao, UserDetailDao, UserRoleDao
from ..database import RoutingDatabase
from ..do import UserDO
from .base import SqlRepository


class SqlUserRepository(SqlRepository[User, UserDO]):
    """``user`` + ``user_detail`` (1:1) + ``user_role`` (links)."""

    def __init__(self, db: RoutingDatabase) -> None:
        self._details = UserDetailDao(db)
        self._users = UserDao(db, self._details)
        super().__init__(db, self._users)
        self._roles = UserRoleDao(db)

    async def load_many(self, rows: list[UserDO]) -> list[User]:
        uuids = [r.user_uuid for r in rows]
        details = {d.user_uuid: d for d in await self._details.list_in(None, "user_uuid", uuids)}
        roles = groupby(lambda r: r.user_uuid, await self._roles.list_in(None, "user_uuid", uuids))
        return [
            self._users.to_entity(r, detail=details.get(r.user_uuid), roles=roles.get(r.user_uuid, [])) for r in rows
        ]

    async def save_children(self, aggregate: User) -> None:
        existing = await self._details.get(aggregate.org_uuid, aggregate.user_uuid)
        self._details.add(self._details.to_do(aggregate.detail, existing))
        await self._roles.sync(
            aggregate.org_uuid,
            ("user_uuid", aggregate.user_uuid),
            ("role_uuid", "project_uuid"),
            {(a.role_uuid, a.project_uuid) for a in aggregate.roles},
            extra={"tenant_uuid": aggregate.tenant_uuid},
        )

    async def delete_children(self, org_uuid: str, uuid: str) -> None:
        await self._details.soft_delete(org_uuid, user_uuid=uuid)
        await self._roles.soft_delete(org_uuid, user_uuid=uuid)

    async def find_by_username(self, org_uuid: str, tenant_uuid: str, username: str) -> Option[User]:
        row = await self._users.find_by_username(org_uuid, tenant_uuid, username)
        return option.NOTHING if row is None else Some((await self.load_many([row]))[0])
