from pydantic import Field
from pydantic_settings import BaseSettings

from ._env import settings_config


class AuthConfig(BaseSettings):
    model_config = settings_config("AUTH_")

    enabled: bool = True  # False => no authentication (local debugging / bootstrapping); X-Operator names the operator
    session_ttl_seconds: int = Field(default=7200, ge=60)  # login token lifetime
    authority_ttl_seconds: int = Field(default=60, ge=1, le=86_400)  # cached roles/permissions; also evicted by events
    platform_org_uuid: str | None = None  # principals of this organization may act on any organization
