"""Test helpers that also narrow types for pyright / Pylance."""

from __future__ import annotations

from typing import Any

from expression import Error, Ok, Result


def ok[T](result: Result[T, Any]) -> T:
    """Unwrap ``Ok`` (fails the test on ``Error``)."""
    if isinstance(result, Ok):
        return result.ok
    raise AssertionError(f"expected Ok, got {result!r}")


def err[E](result: Result[Any, E]) -> E:
    """Unwrap ``Error`` (fails the test on ``Ok``)."""
    if isinstance(result, Error):
        return result.error
    raise AssertionError(f"expected Error, got {result!r}")


def of_type[T](value: object, cls: type[T]) -> T:
    """``assert isinstance`` that returns the narrowed value (e.g. a specific DomainEvent)."""
    assert isinstance(value, cls), f"expected {cls.__name__}, got {type(value).__name__}"
    return value
