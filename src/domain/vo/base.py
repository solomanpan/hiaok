"""Value object building blocks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class ValueObject:
    """Immutable, compared by value, self-validating (``create`` returns a ``Result``)."""


@dataclass(frozen=True, kw_only=True)
class Audit(ValueObject):
    """Read-only audit columns filled by persistence."""

    create_time: datetime | None = None
    update_time: datetime | None = None
    opr: str | None = None
