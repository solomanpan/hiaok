from pydantic_settings import BaseSettings

from ._env import settings_config


class DatabaseConfig(BaseSettings):
    """Write to master, read from slave (``@master`` / ``@slave`` on service methods)."""

    model_config = settings_config("DB_")

    master_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/hiaok"
    slave_url: str | None = None  # None => reads also go to master
    pool_size: int = 10
    max_overflow: int = 20
    pool_recycle: int = 1800
    echo: bool = False

    @property
    def effective_slave_url(self) -> str:
        return self.slave_url or self.master_url
