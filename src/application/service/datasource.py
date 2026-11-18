"""``@master`` / ``@slave``: datasource routing + transaction boundary for application-service methods.

    class RoleService(...):
        @slave
        async def get(...)  -> reads hit the replica, read-only transaction

        @master
        async def grant(...) -> writes hit the primary; commit on Ok, rollback on Error / exception

Rules (implemented by the TransactionManager adapter):
* the OUTERMOST decorated call opens the session; nested decorated calls JOIN it
  (a ``@slave`` call inside ``@master`` reads from master -> read-your-own-writes);
* ``@master`` inside ``@slave`` is a programming error and raises;
* only the root decides: ``Error`` result or exception -> rollback, otherwise commit;
* domain events are published *after* commit (``Transaction.after_commit``).
"""

from __future__ import annotations

import functools
from collections.abc import Awaitable, Callable
from typing import Concatenate

from expression import Error
from hiaok_core.facade import DataSource, HasTransactionManager

type ServiceMethod[S, **P, R] = Callable[Concatenate[S, P], Awaitable[R]]


def _routed(datasource: DataSource):
    def decorator[S: HasTransactionManager, **P, R](fn: ServiceMethod[S, P, R]) -> ServiceMethod[S, P, R]:
        @functools.wraps(fn)
        async def wrapper(self: S, *args: P.args, **kwargs: P.kwargs) -> R:
            async with self.tx.begin(datasource) as tx:
                result = await fn(self, *args, **kwargs)
                if tx.is_root and isinstance(result, Error):
                    tx.set_rollback_only()
                return result

        wrapper.__datasource__ = datasource  # type: ignore[attr-defined]  # introspection / tests
        return wrapper

    return decorator


master = _routed(DataSource.MASTER)
slave = _routed(DataSource.SLAVE)
