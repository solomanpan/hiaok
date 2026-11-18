from __future__ import annotations

from typing import Literal

from pydantic import Field

from ...application.model import CreateSysConfig, SysConfigModel, UpdateSysConfig
from .common import EntityResponse, Keyed, MetaRequest, MetaUpdateRequest, OrgScoped


class SysConfigCreateRequest(OrgScoped, MetaRequest):
    config_key: str = Field(..., examples=["security.password.min_length"])
    config_value: str
    value_type: Literal["string", "int", "bool", "json"] = "string"
    config_group: str | None = None

    def to_command(self) -> CreateSysConfig:
        return CreateSysConfig(**self.model_dump())


class SysConfigUpdateRequest(Keyed, MetaUpdateRequest):
    config_value: str | None = None

    def to_command(self) -> UpdateSysConfig:
        return UpdateSysConfig(**self.patch())


class ConfigKeyRequest(OrgScoped):
    config_key: str


class SysConfigResponse(EntityResponse):
    config_uuid: str
    config_key: str
    config_value: str
    value_type: str
    config_group: str | None = None

    @classmethod
    def of(cls, m: SysConfigModel) -> SysConfigResponse:
        return cls.model_validate(m)
