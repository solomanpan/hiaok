"""Self-validating string value objects.

``X.create(raw)`` validates (input from users); ``X(value)`` trusts (data from the database).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError, validation

from .base import ValueObject

_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,63}$")
# permission codes: "resource:action", wildcard action "resource:*", or "*" (everything)
PERM_CODE = re.compile(r"^(\*|[A-Za-z0-9][A-Za-z0-9_.\-]{0,62}(:([A-Za-z0-9_.\-]{1,62}|\*))?)$")
_USERNAME = re.compile(r"^[A-Za-z0-9_.@\-]{3,64}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^\+?[0-9\-]{7,20}$")


def _match(pattern: re.Pattern[str], raw: str | None, code: str, message: str) -> Result[str, DomainError]:
    value = (raw or "").strip()
    return Ok(value) if pattern.match(value) else Error(validation(code, message))


def non_blank(raw: str | None, field: str, max_len: int = 128) -> Result[str, DomainError]:
    value = (raw or "").strip()
    if not value:
        return Error(validation(f"{field}_required", f"{field} is required"))
    if len(value) > max_len:
        return Error(validation(f"{field}_too_long", f"{field} must be <= {max_len} chars"))
    return Ok(value)


@dataclass(frozen=True)
class Code(ValueObject):
    """org_code / role_code / perm_code (``project:create``) / config_key (``security.min_length``)."""

    value: str

    @staticmethod
    def create(raw: str | None, field: str = "code", pattern: re.Pattern[str] = _CODE) -> Result[Code, DomainError]:
        return _match(pattern, raw, f"invalid_{field}", f"{field} must match {pattern.pattern}").map(Code)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Username(ValueObject):
    value: str

    @staticmethod
    def create(raw: str | None) -> Result[Username, DomainError]:
        return _match(_USERNAME, raw, "invalid_username", "username must be 3-64 chars of [A-Za-z0-9_.@-]").map(
            Username
        )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Email(ValueObject):
    value: str

    @staticmethod
    def create(raw: str | None) -> Result[Email, DomainError]:
        return _match(_EMAIL, raw, "invalid_email", "invalid email address").map(Email)

    @staticmethod
    def optional(raw: str | None) -> Result[Email | None, DomainError]:
        if not raw:
            return Ok(None)
        return Email.create(raw).map(lambda e: e)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PhoneNumber(ValueObject):
    value: str

    @staticmethod
    def create(raw: str | None) -> Result[PhoneNumber, DomainError]:
        return _match(_PHONE, raw, "invalid_phone", "invalid phone number").map(PhoneNumber)

    @staticmethod
    def optional(raw: str | None) -> Result[PhoneNumber | None, DomainError]:
        if not raw:
            return Ok(None)
        return PhoneNumber.create(raw).map(lambda p: p)

    def __str__(self) -> str:
        return self.value


def text_or_none(vo: Email | PhoneNumber | Code | Username | None) -> str | None:
    return None if vo is None else vo.value
