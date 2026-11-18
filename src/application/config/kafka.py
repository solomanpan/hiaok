from pydantic_settings import BaseSettings

from ._env import settings_config


class KafkaConfig(BaseSettings):
    model_config = settings_config("KAFKA_")

    bootstrap_servers: str = "localhost:9094"
    topic: str = "hiaok-events"
    group_id: str = "hiaok"
