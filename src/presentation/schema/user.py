from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field

from ...application.model import (
    AuthorityModel,
    RegisterUser,
    RoleAssignmentModel,
    UpdateUser,
    UserDetailModel,
    UserModel,
)
from .common import EntityResponse, MetaRequest, MetaUpdateRequest, TreeNodeResponse
from .menu import MenuResponse


class UserDetailDTO(BaseModel):
    model_config = {"from_attributes": True}

    nickname: str | None = Field(default=None, max_length=128)
    real_name: str | None = Field(default=None, max_length=128)
    avatar_url: str | None = Field(default=None, max_length=512)
    gender: str | None = Field(default=None, max_length=16)
    birthday: date | None = None
    locale: str | None = Field(default=None, max_length=16)
    timezone: str | None = Field(default=None, max_length=64)

    def to_model(self) -> UserDetailModel:
        return UserDetailModel(**self.model_dump())


class RoleAssignmentDTO(BaseModel):
    model_config = {"from_attributes": True}

    role_uuid: str
    project_uuid: str = Field(default="", description='"" = tenant-wide')

    def to_model(self) -> RoleAssignmentModel:
        return RoleAssignmentModel(self.role_uuid, self.project_uuid)


class UserRegisterRequest(MetaRequest):
    tenant_uuid: str
    username: str = Field(..., examples=["alice"])
    password: str = Field(..., min_length=8, repr=False)
    email: EmailStr | None = None
    phone: str | None = None
    group_uuid: str | None = None
    nickname: str | None = None
    role_uuids: list[str] = Field(default_factory=list)

    def to_command(self, org_uuid: str) -> RegisterUser:
        data = self.model_dump()
        data["role_uuids"] = tuple(self.role_uuids)
        return RegisterUser(org_uuid=org_uuid, **data)


class UserUpdateRequest(MetaUpdateRequest):
    email: EmailStr | None = None
    phone: str | None = None
    group_uuid: str | None = None
    detail: UserDetailDTO | None = None

    def to_command(self) -> UpdateUser:
        return UpdateUser(
            email=self.email,
            phone=self.phone,
            group_uuid=self.group_uuid,
            detail=None if self.detail is None else self.detail.to_model(),
            description=self.description,
            remark=self.remark,
            state=self.state,
        )


class AssignRolesRequest(BaseModel):
    roles: list[RoleAssignmentDTO]


class ChangePasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8, repr=False)


class UserResponse(EntityResponse):
    user_uuid: str
    tenant_uuid: str
    username: str
    email: str | None = None
    phone: str | None = None
    group_uuid: str | None = None
    last_login_time: datetime | None = None
    detail: UserDetailDTO
    roles: list[RoleAssignmentDTO]

    @classmethod
    def of(cls, m: UserModel) -> UserResponse:
        return cls.model_validate(m)


class AuthorityResponse(BaseModel):
    user_uuid: str
    role_codes: list[str]
    permission_codes: list[str]
    menus: list[TreeNodeResponse[MenuResponse]]

    @classmethod
    def of(cls, m: AuthorityModel) -> AuthorityResponse:
        return cls(
            user_uuid=m.user_uuid,
            role_codes=m.role_codes,
            permission_codes=m.permission_codes,
            menus=[TreeNodeResponse[MenuResponse].of(n, MenuResponse.of) for n in m.menus],
        )
