from hiaok_core.facade import Cache

from ...application.config import Settings


def create_cache(settings: Settings) -> Cache:
    if settings.app.cache == "memory":
        from .memory_cache import InMemoryCache

        return InMemoryCache(settings.redis.cache_ttl_seconds)
    from .redis_cache import RedisCache

    return RedisCache(settings.redis)


__all__ = ["create_cache"]
