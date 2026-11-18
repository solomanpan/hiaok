from __future__ import annotations

import asyncio
import contextlib
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from hiaok_core.facade import Event, EventHandler

from ...application.config import KafkaConfig
from .registry import HandlerRegistry, dispatch_with_retry
from .serde import deserialize, require_domain_event, serialize

log = logging.getLogger(__name__)


class KafkaEventBus:
    """One topic, key = aggregate id (per-aggregate ordering), manual commit after handling."""

    def __init__(self, config: KafkaConfig) -> None:
        self._cfg = config
        self._registry = HandlerRegistry()
        self._producer: AIOKafkaProducer | None = None
        self._consumer: AIOKafkaConsumer | None = None
        self._task: asyncio.Task[None] | None = None

    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        self._registry.subscribe(event_type, handler)

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._cfg.bootstrap_servers, acks="all", enable_idempotence=True
        )
        await self._producer.start()
        if self._registry.has_handlers():
            self._consumer = AIOKafkaConsumer(
                self._cfg.topic,
                bootstrap_servers=self._cfg.bootstrap_servers,
                group_id=self._cfg.group_id,
                enable_auto_commit=False,
                auto_offset_reset="earliest",
            )
            await self._consumer.start()
            self._task = asyncio.create_task(self._consume(), name="kafka-event-consumer")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._consumer:
            await self._consumer.stop()
        if self._producer:
            await self._producer.stop()

    async def publish(self, event: Event) -> None:
        assert self._producer, "bus not started"
        await self._producer.send_and_wait(
            self._cfg.topic,
            value=serialize(event).encode(),
            key=require_domain_event(event).aggregate_id.encode(),
            headers=[("event_type", event.event_type().encode())],
        )

    async def _consume(self) -> None:
        assert self._consumer
        async for message in self._consumer:
            if message.value is not None:  # tombstones carry no event
                event = deserialize(message.value)
                if event.is_some() and not await dispatch_with_retry(self._registry, event.value):
                    log.error("giving up on offset %s -> send to a dead-letter topic here", message.offset)
            await self._consumer.commit()
