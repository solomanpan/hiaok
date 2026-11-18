from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from expression import Result
from hiaok_core.exception import DomainError

from ...domain.entity import User, UserDetail
from ...domain.vo import Email, PasswordHash, PhoneNumber, RoleAssignment, Username, text_or_none
from .base import CreateMeta, EntityModel, TreeModel, UpdateMeta, entity_fields, entity_kwargs
from .menu import MenuModel


@dataclass(frozen=True, kw_only=True)
class UserDetailModel:
    nickname: str | None = None
    real_name: str | None = None
    avatar_url: str | None = None
    gender: str | None = None
    birthday: date | None = None
    locale: str | None = None
    timezone: str | None = None

    @classmethod
    def from_domain(cls, d: UserDetail) -> UserDetailModel:
        return cls(
            nickname=d.nickname,
            real_name=d.real_name,
            avatar_url=d.avatar_url,
            gender=d.gender,
            birthday=d.birthday,
            locale=d.locale,
            timezone=d.timezone,
        )

    def to_domain(self, org_uuid: str, user_uuid: str) -> UserDetail:
        return UserDetail(
            org_uuid=org_uuid,
            user_uuid=user_uuid,
            nickname=self.nickname,
            real_name=self.real_name,
            avatar_url=self.avatar_url,
            gender=self.gender,
            birthday=self.birthday,
            locale=self.locale,
            timezone=self.timezone,
        )


@dataclass(frozen=True)
class RoleAssignmentModel:
    role_uuid: str
    project_uuid: str = ""

    def to_domain(self) -> RoleAssignment:
        return RoleAssignment(self.role_uuid, self.project_uuid)


@dataclass(frozen=True, kw_only=True)
class UserModel(EntityModel):
    """Never exposes the password hash."""

    user_uuid: str
    tenant_uuid: str
    username: str
    email: str | None = None
    phone: str | None = None
    group_uuid: str | None = None
    last_login_time: datetime | None = None
    detail: UserDetailModel = field(default_factory=UserDetailModel)
    roles: list[RoleAssignmentModel] = field(default_factory=list)

    @classmethod
    def from_domain(cls, u: User) -> UserModel:
        return cls(
            **entity_fields(u),
            user_uuid=u.user_uuid,
            tenant_uuid=u.tenant_uuid,
            username=u.username.value,
            email=text_or_none(u.email),
            phone=text_or_none(u.phone),
            group_uuid=u.group_uuid,
            last_login_time=u.last_login_time,
            detail=UserDetailModel.from_domain(u.detail),
            roles=[RoleAssignmentModel(a.role_uuid, a.project_uuid) for a in sorted(u.roles)],
        )

    def to_domain(self, password_hash: PasswordHash) -> User:
        return User(
            **entity_kwargs(self),
            user_uuid=self.user_uuid,
            tenant_uuid=self.tenant_uuid,
            username=Username(self.username),
            password_hash=password_hash,
            email=Email(self.email) if self.email else None,
            phone=PhoneNumber(self.phone) if self.phone else None,
            group_uuid=self.group_uuid,
            last_login_time=self.last_login_time,
            detail=self.detail.to_domain(self.org_uuid, self.user_uuid),
            roles=frozenset(r.to_domain() for r in self.roles),
        )


@dataclass(frozen=True, kw_only=True)
class RegisterUser(CreateMeta):
    """``password`` is raw here; the use case validates + hashes it before ``to_domain``."""

    org_uuid: str
    tenant_uuid: str
    username: str
    password: str = field(repr=False)
    email: str | None = None
    phone: str | None = None
    group_uuid: str | None = None
    nickname: str | None = None
    role_uuids: tuple[str, ...] = ()

    def to_domain(self, uuid: str, password_hash: PasswordHash) -> Result[User, DomainError]:
        return User.register(
            self.org_uuid,
            uuid,
            self.tenant_uuid,
            self.username,
            password_hash,
            email=self.email,
            phone=self.phone,
            group_uuid=self.group_uuid,
            nickname=self.nickname,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateUser(UpdateMeta):
    email: str | None = None
    phone: str | None = None
    group_uuid: str | None = None
    detail: UserDetailModel | None = None

    def apply_to(self, u: User) -> Result[User, DomainError]:
        detail = self.detail
        return (
            u.update(email=self.email, phone=self.phone, group_uuid=self.group_uuid)
            .map(lambda x: x if detail is None else x.update_detail(detail.to_domain(x.org_uuid, x.user_uuid)))
            .map(self.apply_meta)
        )


@dataclass(frozen=True)
class AuthorityModel:
    """Effective authorities of a user (union of enabled roles).

    Read-only projection assembled from several aggregates, so it has no ``to_domain``.
    """

    user_uuid: str
    role_codes: list[str]
    permission_codes: list[str]
    menus: list[TreeModel[MenuModel]]
