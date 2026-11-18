from __future__ import annotations

import time

from expression import Option, Some, option


class InMemoryCache:
    """Per-process cache (APP_CACHE=memory): fine for one node / tests, not shared across replicas."""

    def __init__(self, default_ttl: int = 300) -> None:
        self._data: dict[str, tuple[str, float]] = {}
        self._ttl = default_ttl

    async def get(self, key: str) -> Option[str]:
        hit = self._data.get(key)
        if hit is None or hit[1] < time.monotonic():
            self._data.pop(key, None)
            return option.NOTHING
        return Some(hit[0])

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        self._data[key] = (value, time.monotonic() + (ttl_seconds or self._ttl))

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self._data.pop(key, None)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        self._data.clear()
