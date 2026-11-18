from __future__ import annotations

from dataclasses import dataclass

from expression import Error, Ok, Result
from hiaok_core.exception import DomainError, validation

from .base import ValueObject

MIN_PASSWORD_LENGTH = 8


@dataclass(frozen=True)
class RawPassword(ValueObject):
    """Plain text password - validated, never stored, never logged."""

    value: str

    @staticmethod
    def create(raw: str | None) -> Result[RawPassword, DomainError]:
        value = raw or ""
        if len(value) < MIN_PASSWORD_LENGTH:
            return Error(validation("weak_password", f"password must be at least {MIN_PASSWORD_LENGTH} chars"))
        if value.isdigit() or value.isalpha():
            return Error(validation("weak_password", "password must mix letters and digits/symbols"))
        return Ok(RawPassword(value))

    def __repr__(self) -> str:
        return "RawPassword(***)"


@dataclass(frozen=True)
class PasswordHash(ValueObject):
    value: str

    def __repr__(self) -> str:
        return "PasswordHash(***)"
