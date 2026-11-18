import os

from pydantic_settings import SettingsConfigDict

APP_ENV = os.getenv("APP_ENV", "dev")
# later files win: shared .env, then the profile (.env.dev | .env.test | .env.prod)
ENV_FILES = (".env", f".env.{APP_ENV}")


def settings_config(prefix: str) -> SettingsConfigDict:
    return SettingsConfigDict(env_prefix=prefix, env_file=ENV_FILES, extra="ignore")
