"""Publish -> consume round-trip through a real broker."""

import anyio

from src.domain.entity.event import UserPasswordChanged


async def _roundtrip(bus) -> None:
    sent = UserPasswordChanged(org_uuid="it-org", user_uuid="it-user")
    arrived = anyio.Event()

    async def handler(event: UserPasswordChanged) -> None:
        if event.event_id == sent.event_id:
            arrived.set()

    bus.subscribe(UserPasswordChanged, handler)
    await bus.start()
    try:
        await bus.publish(sent)
        with anyio.fail_after(15):
            await arrived.wait()
    finally:
        await bus.stop()


async def test_redis_stream_roundtrip(redis_config):
    from src.infrastructure.messaging.redis_stream import RedisStreamEventBus

    await _roundtrip(RedisStreamEventBus(redis_config))


async def test_kafka_roundtrip(kafka_config):
    from src.infrastructure.messaging.kafka import KafkaEventBus

    await _roundtrip(KafkaEventBus(kafka_config))
