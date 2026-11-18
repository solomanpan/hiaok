from __future__ import annotations

import redis.asyncio as redis
from expression import Option, Some, option

from ...application.config import RedisConfig


class RedisCache:
    def __init__(self, config: RedisConfig) -> None:
        self._client = redis.from_url(config.url, decode_responses=True)  # lazy connection
        self._prefix = config.cache_prefix
        self._ttl = config.cache_ttl_seconds

    async def get(self, key: str) -> Option[str]:
        value = await self._client.get(self._prefix + key)
        return option.NOTHING if value is None else Some(str(value))

    async def set(self, key: str, value: str, ttl_seconds: int | None = None) -> None:
        await self._client.set(self._prefix + key, value, ex=ttl_seconds or self._ttl)

    async def delete(self, *keys: str) -> None:
        if keys:
            await self._client.delete(*(self._prefix + k for k in keys))

    async def start(self) -> None:
        await self._client.ping()

    async def stop(self) -> None:
        await self._client.aclose()
