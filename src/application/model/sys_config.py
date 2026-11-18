from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from expression import Ok, Result
from hiaok_core.exception import DomainError

from ...domain.entity import SysConfig
from ...domain.enum import ConfigValueType
from ...domain.vo import Code
from .base import CreateMeta, EntityModel, UpdateMeta, entity_fields, entity_kwargs


@dataclass(frozen=True, kw_only=True)
class SysConfigModel(EntityModel):
    config_uuid: str
    config_key: str
    config_value: str
    value_type: str = ConfigValueType.STRING
    config_group: str | None = None

    @classmethod
    def from_domain(cls, c: SysConfig) -> SysConfigModel:
        return cls(
            **entity_fields(c),
            config_uuid=c.config_uuid,
            config_key=c.config_key.value,
            config_value=c.config_value,
            value_type=c.value_type.value,
            config_group=c.config_group,
        )

    def to_domain(self) -> SysConfig:
        return SysConfig(
            **entity_kwargs(self),
            config_uuid=self.config_uuid,
            config_key=Code(self.config_key),
            config_value=self.config_value,
            value_type=ConfigValueType(self.value_type),
            config_group=self.config_group,
        )

    # ---- cache codec (used by the read-through cache in SysConfigService) ----
    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, raw: str) -> SysConfigModel:
        data = json.loads(raw)
        data["create_time"] = data["update_time"] = None  # audit timestamps are not cached
        return cls(**data)


@dataclass(frozen=True, kw_only=True)
class CreateSysConfig(CreateMeta):
    org_uuid: str
    config_key: str
    config_value: str
    value_type: str = ConfigValueType.STRING
    config_group: str | None = None

    def to_domain(self, uuid: str) -> Result[SysConfig, DomainError]:
        return SysConfig.create(
            self.org_uuid,
            uuid,
            self.config_key,
            self.config_value,
            value_type=self.value_type,
            config_group=self.config_group,
            description=self.description,
            remark=self.remark,
        )


@dataclass(frozen=True, kw_only=True)
class UpdateSysConfig(UpdateMeta):
    config_value: str | None = None

    def apply_to(self, c: SysConfig) -> Result[SysConfig, DomainError]:
        changed = Ok(c) if self.config_value is None else c.change_value(self.config_value)
        return changed.map(self.apply_meta)
