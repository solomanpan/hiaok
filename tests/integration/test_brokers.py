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


async def test_kafka_routes_each_domain_to_its_own_topic_and_dead_letters_failures(kafka_config):
    """Five domain topics: every event arrives via its own topic; a handler that keeps failing -> ``<topic>.dlq``."""
    from aiokafka import AIOKafkaConsumer

    from src.domain.entity.event import EntityCreated
    from src.infrastructure.messaging.kafka import KafkaEventBus
    from src.infrastructure.messaging.topics import Topic

    bus = KafkaEventBus(kafka_config)
    entity_of = {
        Topic.ORGANIZATION: "Tenant",
        Topic.IDENTITY: "User",
        Topic.AUTHORIZATION: "Role",
        Topic.HR: "Employee",
        Topic.CONFIG: "SysConfig",
    }
    sent = {
        topic: EntityCreated(org_uuid="it-org", entity_type=e, entity_uuid=f"it-{topic.value}")
        for topic, e in entity_of.items()
    }
    arrived: set[str] = set()
    all_healthy_arrived = anyio.Event()

    async def record(event: EntityCreated) -> None:
        if event.event_id in {e.event_id for e in sent.values()}:
            if event.entity_type == "Employee":
                raise RuntimeError("poison")  # the HR topic must dead-letter this one
            arrived.add(event.event_id)
            if len(arrived) == len(sent) - 1:
                all_healthy_arrived.set()

    bus.subscribe(EntityCreated, record)
    await bus.start()
    try:
        for event in sent.values():
            await bus.publish(event)
        with anyio.fail_after(30):
            await all_healthy_arrived.wait()

        dead = AIOKafkaConsumer(
            bus.dlq_name(Topic.HR),
            bootstrap_servers=kafka_config.bootstrap_servers,
            group_id=f"{kafka_config.group_id}.dlq-check",
            auto_offset_reset="earliest",
        )
        await dead.start()
        try:
            with anyio.fail_after(30):
                async for message in dead:
                    if sent[Topic.HR].event_id.encode() in (message.value or b""):
                        assert dict(message.headers)["source_topic"] == bus.topic_name(Topic.HR).encode()
                        break
        finally:
            await dead.stop()
    finally:
        await bus.stop()
