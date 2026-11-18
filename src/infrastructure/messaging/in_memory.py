from __future__ import annotations

from hiaok_core.facade import Event, EventHandler

from .registry import HandlerRegistry


class InMemoryEventBus:
    """In-process, synchronous: for local runs / tests without Redis or Kafka (APP_BROKER=memory)."""

    def __init__(self) -> None:
        self._registry = HandlerRegistry()
        self.published: list[Event] = []

    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        self._registry.subscribe(event_type, handler)

    async def publish(self, event: Event) -> None:
        self.published.append(event)
        await self._registry.dispatch(event)

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    def __repr__(self) -> str:
        return f"InMemoryEventBus(published={len(self.published)})"
