"""Test helpers that also narrow types for pyright / Pylance."""

from __future__ import annotations

from typing import Any

from expression import Error, Ok, Option, Result, option


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


class FakeTx:
    def __init__(self, manager: FakeTransactionManager, datasource, is_root: bool) -> None:
        self._manager, self.datasource, self.is_root = manager, datasource, is_root

    def set_rollback_only(self) -> None:
        self._manager.rollback_only = True

    def after_commit(self, callback) -> None:
        self._manager.callbacks.append(callback)


class FakeTransactionManager:
    """Just enough of ``TransactionManager`` for ``@master`` / ``@slave``: nesting joins, ``Error`` => rollback."""

    def __init__(self) -> None:
        self.depth = 0
        self.rollback_only = False
        self.rollbacks = 0
        self.commits = 0
        self.callbacks: list[Any] = []

    def begin(self, datasource):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def scope():
            root = self.depth == 0
            if root:
                self.rollback_only = False
            self.depth += 1
            try:
                yield FakeTx(self, datasource, root)
            finally:
                self.depth -= 1
                if root:
                    self.rollbacks += self.rollback_only
                    self.commits += not self.rollback_only

        return scope()

    def current(self) -> Option[Any]:
        return option.of_obj(None)
