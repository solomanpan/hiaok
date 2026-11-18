from dataclasses import dataclass, field
from functools import lru_cache

from .app import AppConfig
from .database import DatabaseConfig
from .kafka import KafkaConfig
from .redis import RedisConfig


@dataclass(frozen=True)
class Settings:
    app: AppConfig = field(default_factory=AppConfig)
    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    kafka: KafkaConfig = field(default_factory=KafkaConfig)


@lru_cache
def get_settings() -> Settings:
    return Settings()


__all__ = ["AppConfig", "DatabaseConfig", "KafkaConfig", "RedisConfig", "Settings", "get_settings"]
