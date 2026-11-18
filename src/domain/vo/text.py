"""Self-validating string value objects.

``X.create(raw)`` validates (input from users); ``X(value)`` trusts (data from the database).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog, ErrorSpec

from .base import ValueObject


class TextErrors(ErrorCatalog):
    required = ErrorSpec.validation("{field}_required", "{field} is required")
    too_long = ErrorSpec.validation("{field}_too_long", "{field} must be <= {max_len} chars")
    invalid_code = ErrorSpec.validation("invalid_{field}", "{field} must match {pattern}")
    invalid_username = ErrorSpec.validation("invalid_username", "username must be 3-64 chars of [A-Za-z0-9_.@-]")
    invalid_email = ErrorSpec.validation("invalid_email", "invalid email address")
    invalid_phone = ErrorSpec.validation("invalid_phone", "invalid phone number")


_CODE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:\-]{0,63}$")
# permission codes: "resource:action", wildcard action "resource:*", or "*" (everything)
PERM_CODE = re.compile(r"^(\*|[A-Za-z0-9][A-Za-z0-9_.\-]{0,62}(:([A-Za-z0-9_.\-]{1,62}|\*))?)$")
_USERNAME = re.compile(r"^[A-Za-z0-9_.@\-]{3,64}$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_PHONE = re.compile(r"^\+?[0-9\-]{7,20}$")


def _match(pattern: re.Pattern[str], raw: str | None, error: DomainError) -> Result[str, DomainError]:
    value = (raw or "").strip()
    return Ok(value) if pattern.match(value) else Error(error)


def non_blank(raw: str | None, field: str, max_len: int = 128) -> Result[str, DomainError]:
    value = (raw or "").strip()
    if not value:
        return TextErrors.required.err(field=field)
    if len(value) > max_len:
        return TextErrors.too_long.err(field=field, max_len=max_len)
    return Ok(value)


@dataclass(frozen=True)
class Code(ValueObject):
    """org_code / role_code / perm_code (``project:create``) / config_key (``security.min_length``)."""

    value: str

    @staticmethod
    def create(raw: str | None, field: str = "code", pattern: re.Pattern[str] = _CODE) -> Result[Code, DomainError]:
        return _match(pattern, raw, TextErrors.invalid_code(field=field, pattern=pattern.pattern)).map(Code)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Username(ValueObject):
    value: str

    @staticmethod
    def create(raw: str | None) -> Result[Username, DomainError]:
        return _match(_USERNAME, raw, TextErrors.invalid_username()).map(Username)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Email(ValueObject):
    value: str

    @staticmethod
    def create(raw: str | None) -> Result[Email, DomainError]:
        return _match(_EMAIL, raw, TextErrors.invalid_email()).map(Email)

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
        return _match(_PHONE, raw, TextErrors.invalid_phone()).map(PhoneNumber)

    @staticmethod
    def optional(raw: str | None) -> Result[PhoneNumber | None, DomainError]:
        if not raw:
            return Ok(None)
        return PhoneNumber.create(raw).map(lambda p: p)

    def __str__(self) -> str:
        return self.value


def text_or_none(vo: Email | PhoneNumber | Code | Username | None) -> str | None:
    return None if vo is None else vo.value
