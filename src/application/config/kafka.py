from pydantic_settings import BaseSettings

from ._env import settings_config


class KafkaConfig(BaseSettings):
    model_config = settings_config("KAFKA_")

    bootstrap_servers: str = "localhost:9094"
    topic_prefix: str = "hiaok"  # topics: <prefix>.organization / identity / authorization / hr / config
    group_id: str = "hiaok"  # consumer group per topic: <group_id>.<topic>
    dlq_suffix: str = ".dlq"  # dead letters of <topic> go to <topic><suffix>
    create_topics: bool = True  # create the topics (and their dead-letter topics) at startup if missing
    num_partitions: int = 3
    replication_factor: int = 1
