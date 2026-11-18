"""Shared fixtures for every test layer."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest

from src.infrastructure.cache.memory_cache import InMemoryCache
from src.infrastructure.messaging.in_memory import InMemoryEventBus

ORG = "org-1"
TENANT = "tenant-1"


@pytest.fixture
def org_uuid() -> str:
    return ORG


@pytest.fixture
def bus() -> InMemoryEventBus:
    return InMemoryEventBus()


@pytest.fixture
async def cache() -> AsyncGenerator[InMemoryCache, None]:
    c = InMemoryCache(default_ttl=60)
    await c.start()
    yield c
    await c.stop()
