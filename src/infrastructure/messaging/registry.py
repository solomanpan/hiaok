from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

import anyio
from hiaok_core.context import request_context
from hiaok_core.facade import Event, EventHandler

log = logging.getLogger(__name__)


class HandlerRegistry:
    """Local subscription table shared by every bus implementation."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler[Any]]] = defaultdict(list)

    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        self._handlers[event_type.event_type()].append(handler)

    def has_handlers(self) -> bool:
        return bool(self._handlers)

    async def dispatch(self, event: Event) -> None:
        with request_context(operator="event-consumer", trace_id=event.event_id):
            for handler in self._handlers.get(event.event_type(), ()):
                await handler(event)


async def dispatch_with_retry(
    registry: HandlerRegistry, event: Event, *, retries: int = 3, base_delay: float = 0.2
) -> bool:
    for attempt in range(1, retries + 1):
        try:
            await registry.dispatch(event)
            return True
        except Exception:
            log.exception("handler failed for %s (attempt %d/%d)", event.event_type(), attempt, retries)
            await anyio.sleep(base_delay * attempt)
    return False
