from hiaok_core.facade import EventBus

from ...application.config import Settings


def create_event_bus(settings: Settings) -> EventBus:
    """APP_BROKER=redis | kafka | memory (adapters are imported lazily)."""
    match settings.app.broker:
        case "kafka":
            from .kafka import KafkaEventBus

            return KafkaEventBus(settings.kafka)
        case "memory":
            from .in_memory import InMemoryEventBus

            return InMemoryEventBus()
        case _:
            from .redis_stream import RedisStreamEventBus

            return RedisStreamEventBus(settings.redis)


__all__ = ["create_event_bus"]
