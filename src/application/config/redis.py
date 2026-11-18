from pydantic_settings import BaseSettings

from ._env import settings_config


class RedisConfig(BaseSettings):
    model_config = settings_config("REDIS_")

    url: str = "redis://localhost:6379/0"
    # event bus (Redis Streams)
    stream: str = "hiaok-events"
    consumer_group: str = "hiaok"
    consumer_name: str = "consumer-1"
    stream_maxlen: int = 100_000
    # cache
    cache_prefix: str = "hiaok:"
    cache_ttl_seconds: int = 300
