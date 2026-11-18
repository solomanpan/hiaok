from __future__ import annotations

from collections.abc import Iterable

from expression import Option, Result
from hiaok_core.exception import DomainError
from hiaok_core.facade import EventPublisher, IdGenerator, TransactionManager
from hiaok_core.fp import AsyncResult

from ...domain.entity import User
from ...domain.repository import UserRepository
from ...domain.vo import PasswordHash, RoleAssignment
from ..model import RegisterUser
from .base import CrudService
from .datasource import master, slave
from .ids import next_id


class UserService(CrudService[User]):
    entity = "User"

    def __init__(
        self,
        tx: TransactionManager,
        repository: UserRepository,
        publisher: EventPublisher,
        new_id: IdGenerator = next_id,
    ) -> None:
        super().__init__(tx, repository, publisher, new_id)
        self._users = repository

    @master
    async def register(
        self, cmd: RegisterUser, password_hash: PasswordHash, roles: Iterable[RoleAssignment] = ()
    ) -> Result[User, DomainError]:
        return await (
            AsyncResult.of(cmd.to_domain(self._new_id(), password_hash))
            .bind(lambda u: u.assign_roles(roles))
            .bind(self.save)
        )

    @master
    async def assign_roles(
        self, org_uuid: str, user_uuid: str, roles: Iterable[RoleAssignment]
    ) -> Result[User, DomainError]:
        return (
            await AsyncResult.of(self.load(org_uuid, user_uuid)).bind(lambda u: u.assign_roles(roles)).bind(self.save)
        )

    @master
    async def change_password(self, org_uuid: str, user_uuid: str, new_hash: PasswordHash) -> Result[User, DomainError]:
        return await (
            AsyncResult.of(self.load(org_uuid, user_uuid)).map(lambda u: u.change_password(new_hash)).bind(self.save)
        )

    @slave
    async def find_by_username(self, org_uuid: str, tenant_uuid: str, username: str) -> Option[User]:
        return await self._users.find_by_username(org_uuid, tenant_uuid, username)
