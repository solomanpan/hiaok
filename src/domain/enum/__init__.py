"""Domain enumerations (stored as SMALLINT / VARCHAR columns)."""

from enum import IntEnum, StrEnum

__all__ = ["ConfigValueType", "LogType", "MenuType", "PermType", "RoleType", "Status"]


class Status(IntEnum):
    """``state`` SMALLINT column."""

    ENABLED = 0
    DISABLED = 1


class RoleType(IntEnum):
    SYSTEM = 0  # built-in, cannot be deleted
    CUSTOM = 1


class PermType(IntEnum):
    API = 0
    BUTTON = 1
    DATA = 2


class MenuType(IntEnum):
    DIRECTORY = 0
    MENU = 1
    BUTTON = 2


class ConfigValueType(StrEnum):
    STRING = "string"
    INT = "int"
    BOOL = "bool"
    JSON = "json"


class LogType(StrEnum):
    EVENT = "event"
    COMMAND = "command"  # outcome of an asynchronous write request (success / failure)
    OPERATION = "operation"
    LOGIN = "login"
