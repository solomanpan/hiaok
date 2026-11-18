from typing import Literal

from pydantic_settings import BaseSettings

from ._env import APP_ENV, settings_config


class AppConfig(BaseSettings):
    model_config = settings_config("APP_")

    name: str = "hiaok"
    env: str = APP_ENV
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    broker: Literal["redis", "kafka", "memory"] = "redis"
    cache: Literal["redis", "memory"] = "redis"
    consume_events: bool = True  # False => API node only publishes; run `hiaok worker` to consume
    docs_enabled: bool = True  # /docs, /redoc, /openapi.json (set APP_DOCS_ENABLED=false in prod if not public)
