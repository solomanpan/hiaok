from __future__ import annotations

from collections.abc import Generator, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from expression import Ok, Result, effect
from hiaok_core.exception import DomainError

from ..vo import Email, PasswordHash, PhoneNumber, RoleAssignment, Username
from .base import AggregateRoot
from .event import UserPasswordChanged, UserRegistered, UserRolesAssigned
from .user_detail import UserDetail


@dataclass(frozen=True, kw_only=True)
class User(AggregateRoot):
    """``user`` + ``user_detail`` (entity) + ``user_role`` (value objects)."""

    user_uuid: str
    tenant_uuid: str
    username: Username
    password_hash: PasswordHash
    email: Email | None = None
    phone: PhoneNumber | None = None
    group_uuid: str | None = None
    last_login_time: datetime | None = None
    detail: UserDetail
    roles: frozenset[RoleAssignment] = field(default_factory=frozenset)

    @property
    def uuid(self) -> str:
        return self.user_uuid

    @staticmethod
    def register(
        org_uuid: str,
        user_uuid: str,
        tenant_uuid: str,
        username: str,
        password_hash: PasswordHash,
        *,
        email: str | None = None,
        phone: str | None = None,
        group_uuid: str | None = None,
        nickname: str | None = None,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[User, DomainError]:
        @effect.result[User, DomainError]()
        def build() -> Generator[Any, Any, User]:
            name = yield from Username.create(username)
            mail = yield from Email.optional(email)
            tel = yield from PhoneNumber.optional(phone)
            user = User(
                org_uuid=org_uuid,
                user_uuid=user_uuid,
                tenant_uuid=tenant_uuid,
                username=name,
                password_hash=password_hash,
                email=mail,
                phone=tel,
                group_uuid=group_uuid,
                detail=UserDetail(org_uuid=org_uuid, user_uuid=user_uuid, nickname=nickname),
                description=description,
                remark=remark,
            )
            return user.created().record(
                UserRegistered(org_uuid=org_uuid, user_uuid=user_uuid, tenant_uuid=tenant_uuid, username=name.value)
            )

        return build()

    def update(
        self, *, email: str | None = None, phone: str | None = None, group_uuid: str | None = None
    ) -> Result[User, DomainError]:
        @effect.result[User, DomainError]()
        def build() -> Generator[Any, Any, User]:
            mail = (yield from Email.optional(email)) if email is not None else self.email
            tel = (yield from PhoneNumber.optional(phone)) if phone is not None else self.phone
            return self.changed(email=mail, phone=tel, group_uuid=group_uuid or self.group_uuid)

        return build()

    def update_detail(self, detail: UserDetail) -> User:
        return self.changed(detail=detail)

    def assign_roles(self, assignments: Iterable[RoleAssignment]) -> Result[User, DomainError]:
        new_roles = frozenset(assignments)
        if new_roles == self.roles:
            return Ok(self)
        return Ok(
            self.changed(roles=new_roles).record(
                UserRolesAssigned(
                    org_uuid=self.org_uuid,
                    user_uuid=self.user_uuid,
                    role_uuids=tuple(sorted({a.role_uuid for a in new_roles})),
                )
            )
        )

    def role_uuids(self, project_uuid: str | None = None) -> frozenset[str]:
        """Tenant-wide roles plus, when given, the roles granted inside ``project_uuid``."""
        return frozenset(
            a.role_uuid
            for a in self.roles
            if a.tenant_wide or (project_uuid is not None and a.project_uuid == project_uuid)
        )

    def change_password(self, new_hash: PasswordHash) -> User:
        return self.changed(password_hash=new_hash).record(
            UserPasswordChanged(org_uuid=self.org_uuid, user_uuid=self.user_uuid)
        )

    def record_login(self, at: datetime) -> User:
        return self.changed(last_login_time=at)
