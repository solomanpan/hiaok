from __future__ import annotations

import json
from collections.abc import Generator
from dataclasses import dataclass
from typing import Any

from expression import Ok, Result, effect
from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog, ErrorSpec

from ..enum import ConfigValueType
from ..vo import Code
from .base import AggregateRoot
from .event import SysConfigChanged

_BOOLS = {"true": True, "false": False, "1": True, "0": False}


class SysConfigErrors(ErrorCatalog):
    invalid_value_type = ErrorSpec.validation("invalid_value_type", "unknown value_type '{value_type}'")
    invalid_value = ErrorSpec.validation("invalid_config_value", "'{value}' is not a valid {value_type}")


def parse_value(value: str, value_type: ConfigValueType | str) -> Result[Any, DomainError]:
    try:
        value_type = ConfigValueType(value_type)
    except ValueError:
        return SysConfigErrors.invalid_value_type.err(value_type=value_type)
    try:
        match value_type:
            case ConfigValueType.INT:
                return Ok(int(value))
            case ConfigValueType.BOOL:
                return Ok(_BOOLS[value.strip().lower()])
            case ConfigValueType.JSON:
                return Ok(json.loads(value))
            case ConfigValueType.STRING:
                return Ok(value)
    except (ValueError, KeyError):
        pass
    return SysConfigErrors.invalid_value.err(value=value, value_type=value_type.value)


@dataclass(frozen=True, kw_only=True)
class SysConfig(AggregateRoot):
    config_uuid: str
    config_key: Code
    config_value: str
    value_type: ConfigValueType = ConfigValueType.STRING
    config_group: str | None = None

    @property
    def uuid(self) -> str:
        return self.config_uuid

    @staticmethod
    def create(
        org_uuid: str,
        config_uuid: str,
        config_key: str,
        config_value: str,
        *,
        value_type: ConfigValueType | str = ConfigValueType.STRING,
        config_group: str | None = None,
        description: str | None = None,
        remark: str | None = None,
    ) -> Result[SysConfig, DomainError]:
        @effect.result[SysConfig, DomainError]()
        def build() -> Generator[Any, Any, SysConfig]:
            key = yield from Code.create(config_key, "config_key")
            yield from parse_value(config_value, value_type)
            config = SysConfig(
                org_uuid=org_uuid,
                config_uuid=config_uuid,
                config_key=key,
                config_value=config_value,
                value_type=ConfigValueType(value_type),
                config_group=config_group,
                description=description,
                remark=remark,
            )
            return config.created()

        return build()

    def change_value(self, config_value: str) -> Result[SysConfig, DomainError]:
        if config_value == self.config_value:
            return Ok(self)
        return parse_value(config_value, self.value_type).map(
            lambda _: self.changed(config_value=config_value).record(
                SysConfigChanged(org_uuid=self.org_uuid, config_key=self.config_key.value, config_value=config_value)
            )
        )

    def typed_value(self) -> Result[Any, DomainError]:
        return parse_value(self.config_value, self.value_type)
