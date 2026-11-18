"""Process-wide adapters opened once at startup (FastAPI lifespan / worker) and closed at shutdown."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from hiaok_core.facade import Cache, EventBus, PasswordHasher, TransactionManager

from ..application.config import Settings
from .cache import create_cache
from .database import RoutingDatabase, SqlAlchemyTransactionManager
from .messaging import create_event_bus
from .security import ScryptPasswordHasher


@dataclass(frozen=True)
class Resources:
    settings: Settings
    db: RoutingDatabase
    tx: TransactionManager
    bus: EventBus
    cache: Cache
    hasher: PasswordHasher


def build_resources(settings: Settings) -> Resources:
    """Construct only (no I/O): subscribe event handlers on ``bus`` before ``open_resources``."""
    db = RoutingDatabase(settings.db)
    return Resources(
        settings=settings,
        db=db,
        tx=SqlAlchemyTransactionManager(db),
        bus=create_event_bus(settings),
        cache=create_cache(settings),
        hasher=ScryptPasswordHasher(),
    )


@asynccontextmanager
async def open_resources(resources: Resources) -> AsyncGenerator[Resources, None]:
    await resources.cache.start()
    await resources.bus.start()
    try:
        yield resources
    finally:
        await resources.bus.stop()
        await resources.cache.stop()
        await resources.db.dispose()
