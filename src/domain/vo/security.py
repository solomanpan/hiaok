from __future__ import annotations

from dataclasses import dataclass

from expression import Ok, Result
from hiaok_core.exception import DomainError
from hiaok_core.factory import ErrorCatalog, ErrorSpec

from .base import ValueObject


class PasswordErrors(ErrorCatalog):
    weak = ErrorSpec.validation("weak_password", "password {reason}")


MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True)
class RawPassword(ValueObject):
    """Plain text password - validated, never stored, never logged."""

    value: str

    @staticmethod
    def create(raw: str | None) -> Result[RawPassword, DomainError]:
        value = raw or ""
        if len(value) < MIN_PASSWORD_LENGTH:
            return PasswordErrors.weak.err(reason=f"must be at least {MIN_PASSWORD_LENGTH} chars")
        if value.isdigit() or value.isalpha():
            return PasswordErrors.weak.err(reason="must mix letters and digits/symbols")
        return Ok(RawPassword(value))

    def __repr__(self) -> str:
        return "RawPassword(***)"


@dataclass(frozen=True)
class PasswordHash(ValueObject):
    value: str

    def __repr__(self) -> str:
        return "PasswordHash(***)"
