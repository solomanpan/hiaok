from __future__ import annotations

from typing import Literal

from pydantic import Field

from ...application.model import CreateSysConfig, SysConfigModel, UpdateSysConfig
from .common import EntityResponse, MetaRequest, MetaUpdateRequest


class SysConfigCreateRequest(MetaRequest):
    config_key: str = Field(..., examples=["security.password.min_length"])
    config_value: str
    value_type: Literal["string", "int", "bool", "json"] = "string"
    config_group: str | None = None

    def to_command(self, org_uuid: str) -> CreateSysConfig:
        return CreateSysConfig(org_uuid=org_uuid, **self.model_dump())


class SysConfigUpdateRequest(MetaUpdateRequest):
    config_value: str | None = None

    def to_command(self) -> UpdateSysConfig:
        return UpdateSysConfig(**self.model_dump())


class SysConfigResponse(EntityResponse):
    config_uuid: str
    config_key: str
    config_value: str
    value_type: str
    config_group: str | None = None

    @classmethod
    def of(cls, m: SysConfigModel) -> SysConfigResponse:
        return cls.model_validate(m)
