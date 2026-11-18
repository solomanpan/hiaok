from hiaok_core.context import current_context

from src.domain.entity.event import EntityCreated, UserPasswordChanged
from src.infrastructure.messaging.registry import HandlerRegistry, dispatch_with_retry


async def test_in_memory_bus_dispatches_by_type(bus):
    seen = []

    async def handler(event):
        seen.append((event, current_context().operator))

    bus.subscribe(UserPasswordChanged, handler)
    event = UserPasswordChanged(org_uuid="o1", user_uuid="u1")
    await bus.publish(event)
    await bus.publish(EntityCreated(org_uuid="o1", entity_type="Role", entity_uuid="r1"))

    assert seen == [(event, "event-consumer")]
    assert len(bus.published) == 2


async def test_dispatch_with_retry_recovers_then_gives_up():
    calls = 0

    async def flaky(_event):
        nonlocal calls
        calls += 1
        if calls < 2:
            raise RuntimeError("boom")

    registry = HandlerRegistry()
    registry.subscribe(UserPasswordChanged, flaky)
    event = UserPasswordChanged(org_uuid="o1", user_uuid="u1")
    assert await dispatch_with_retry(registry, event, retries=3, base_delay=0) is True
    assert calls == 2

    async def always_fail(_event):
        raise RuntimeError("boom")

    failing = HandlerRegistry()
    failing.subscribe(UserPasswordChanged, always_fail)
    assert await dispatch_with_retry(failing, event, retries=2, base_delay=0) is False


def test_event_aggregate_id_is_kafka_key():
    assert UserPasswordChanged(org_uuid="o1", user_uuid="u1").aggregate_id == "u1"
