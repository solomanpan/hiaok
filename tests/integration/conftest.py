"""Integration tests need real services: ``docker compose up -d`` (add ``--profile kafka`` for Kafka).

Every test here is auto-marked ``integration`` and skipped when its service port is unreachable,
so ``pytest`` stays green on a laptop without Docker.
"""

from __future__ import annotations

import socket
from urllib.parse import urlparse

import pytest

from src.application.config import KafkaConfig, RedisConfig


def _reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "/integration/" in str(item.path):
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def redis_config() -> RedisConfig:
    cfg = RedisConfig(stream="hiaok-it-events", consumer_group="hiaok-it")
    url = urlparse(cfg.url)
    if not _reachable(url.hostname or "localhost", url.port or 6379):
        pytest.skip(f"redis not reachable at {cfg.url}")
    return cfg


@pytest.fixture
def kafka_config() -> KafkaConfig:
    cfg = KafkaConfig(topic_prefix="hiaok-it", group_id="hiaok-it")
    host, _, port = cfg.bootstrap_servers.split(",")[0].partition(":")
    if not _reachable(host, int(port or 9092)):
        pytest.skip(f"kafka not reachable at {cfg.bootstrap_servers}")
    return cfg
