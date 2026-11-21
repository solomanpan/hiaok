from __future__ import annotations

from pydantic import Field

from ...application.model import AuthorityModel, LoginCommand, LoginResult, Principal
from .common import ApiModel, OrgScoped, TreeNodeResponse
from .menu import MenuResponse


class LoginRequest(OrgScoped):
    tenant_uuid: str = Field(..., examples=["tenant-1"])
    username: str = Field(..., min_length=1, max_length=64, examples=["alice"])
    password: str = Field(..., min_length=1, max_length=128, repr=False)
    captcha_id: str | None = Field(default=None, description="from POST /auth/captcha; needed when captcha is required")
    captcha_code: str | None = Field(default=None, max_length=16)

    def to_command(self) -> LoginCommand:
        return LoginCommand(self.org_uuid, self.tenant_uuid, self.username, self.password)


class CaptchaResponse(ApiModel):
    required: bool = Field(description="false: captcha is switched off, send no captchaId / captchaCode")
    captcha_id: str | None = None
    image: str | None = Field(default=None, description="data: URI of an SVG image")
    expires_in: int | None = Field(default=None, description="seconds")


class LoginResponse(ApiModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(..., description="seconds")
    user_uuid: str

    @classmethod
    def of(cls, result: LoginResult) -> LoginResponse:
        return cls(access_token=result.access_token, expires_in=result.expires_in, user_uuid=result.user_uuid)


class EmptyRequest(ApiModel):
    """``reqInfo`` of calls that need no parameters: send ``{}``."""


class PrincipalResponse(ApiModel):
    user_uuid: str
    org_uuid: str
    tenant_uuid: str
    role_codes: list[str]
    permission_codes: list[str]
    menus: list[TreeNodeResponse[MenuResponse]] = Field(
        description="menu tree the user may see (union of enabled roles)"
    )

    @classmethod
    def of(cls, principal: Principal, authority: AuthorityModel | None = None) -> PrincipalResponse:
        """``authority`` carries the menu tree; without it (authentication off) the menus are empty."""
        return cls(
            user_uuid=principal.user_uuid,
            org_uuid=principal.org_uuid,
            tenant_uuid=principal.tenant_uuid,
            role_codes=sorted(principal.role_codes),
            permission_codes=sorted(principal.permission_codes),
            menus=[TreeNodeResponse[MenuResponse].of(n, MenuResponse.of) for n in authority.menus] if authority else [],
        )
