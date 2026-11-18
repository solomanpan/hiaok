"""Read/write splitting: two engines (master = primary, slave = replica) + a ContextVar-scoped session.

``SqlAlchemyTransactionManager`` implements the ``hiaok_core.facade.TransactionManager`` facade used by ``@master`` /
``@slave``. Repositories/DAOs never open sessions themselves: they take ``RoutingDatabase.session`` -
the session of the scope opened by the outermost decorated service method.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field

from expression import Option, option
from hiaok_core.facade import DataSource
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from ...application.config import DatabaseConfig

log = logging.getLogger(__name__)


class DataSourceRoutingError(RuntimeError):
    pass


class NoActiveScopeError(RuntimeError):
    pass


@dataclass
class _Scope:
    datasource: DataSource
    session: AsyncSession
    rollback_only: bool = False
    callbacks: list[Callable[[], Awaitable[None]]] = field(default_factory=list)

    @property
    def is_root(self) -> bool:
        return True

    def set_rollback_only(self) -> None:
        self.rollback_only = True

    def after_commit(self, callback: Callable[[], Awaitable[None]]) -> None:
        self.callbacks.append(callback)


@dataclass
class _Joined:
    """View handed to nested decorated calls: shares the root session, cannot decide commit/rollback."""

    root: _Scope

    @property
    def datasource(self) -> DataSource:
        return self.root.datasource

    @property
    def is_root(self) -> bool:
        return False

    def set_rollback_only(self) -> None:
        self.root.set_rollback_only()

    def after_commit(self, callback: Callable[[], Awaitable[None]]) -> None:
        self.root.after_commit(callback)


_current: ContextVar[_Scope | None] = ContextVar("hiaok_db_scope", default=None)


class RoutingDatabase:
    def __init__(self, config: DatabaseConfig) -> None:
        common = {
            "pool_pre_ping": True,
            "pool_size": config.pool_size,
            "max_overflow": config.max_overflow,
            "pool_recycle": config.pool_recycle,
            "echo": config.echo,
        }
        self.master: AsyncEngine = create_async_engine(config.master_url, **common)
        # read-only at the driver level: a write inside @slave fails even when slave_url == master_url
        self.slave: AsyncEngine = create_async_engine(config.effective_slave_url, **common).execution_options(
            postgresql_readonly=True
        )
        self._factories = {
            DataSource.MASTER: async_sessionmaker(self.master, expire_on_commit=False, autoflush=False),
            DataSource.SLAVE: async_sessionmaker(self.slave, expire_on_commit=False, autoflush=False),
        }

    def session_factory(self, datasource: DataSource) -> async_sessionmaker[AsyncSession]:
        return self._factories[datasource]

    @property
    def session(self) -> AsyncSession:
        scope = _current.get()
        if scope is None:
            raise NoActiveScopeError(
                "no database scope: call repositories from a service method decorated with @master / @slave"
            )
        return scope.session

    async def ping(self) -> dict[str, str | bool]:
        status: dict[str, str | bool] = {}
        for name, engine in (("master", self.master), ("slave", self.slave)):
            try:
                async with engine.connect() as conn:
                    in_recovery = (await conn.execute(text("select pg_is_in_recovery()"))).scalar_one()
                status[name] = "ok"
                status[f"{name}_in_recovery"] = bool(in_recovery)
            except Exception as exc:
                status[name] = f"error: {type(exc).__name__}"
        return status

    async def dispose(self) -> None:
        await self.master.dispose()
        await self.slave.dispose()


class SqlAlchemyTransactionManager:
    def __init__(self, db: RoutingDatabase) -> None:
        self._db = db

    def current(self) -> Option[_Scope | _Joined]:
        scope = _current.get()
        return option.of_obj(scope)

    @asynccontextmanager
    async def begin(self, datasource: DataSource) -> AsyncGenerator[_Scope | _Joined, None]:
        outer = _current.get()
        if outer is not None:
            if outer.datasource is DataSource.SLAVE and datasource is DataSource.MASTER:
                raise DataSourceRoutingError("@master method called inside a @slave scope (read-only replica)")
            yield _Joined(outer)  # @slave inside @master reads from master: read-your-own-writes
            return

        scope = _Scope(datasource, self._db.session_factory(datasource)())
        token = _current.set(scope)
        committed = False
        try:
            async with scope.session:
                try:
                    yield scope
                except BaseException:
                    await scope.session.rollback()
                    raise
                if datasource is DataSource.MASTER and not scope.rollback_only:
                    await scope.session.commit()
                    committed = True
                else:
                    await scope.session.rollback()  # replica: nothing to commit; Error result: discard
        finally:
            _current.reset(token)
        if committed:
            for callback in scope.callbacks:  # outside the scope: callbacks may open their own scopes
                try:
                    await callback()
                except Exception:
                    log.exception("after-commit callback failed (the transaction is already committed)")
