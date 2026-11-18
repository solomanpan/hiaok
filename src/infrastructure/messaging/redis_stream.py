from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import Any, cast

import redis.asyncio as redis
from hiaok_core.facade import Event, EventHandler
from redis.exceptions import ResponseError

from ...application.config import RedisConfig
from .registry import HandlerRegistry, dispatch_with_retry
from .serde import deserialize, serialize

log = logging.getLogger(__name__)


class RedisStreamEventBus:
    """Redis Streams + consumer group. At-least-once: a failed message stays in the PEL (XPENDING)."""

    def __init__(self, config: RedisConfig, *, block_ms: int = 1000) -> None:
        self._cfg = config
        self._block_ms = block_ms
        self._registry = HandlerRegistry()
        self._client: redis.Redis | None = None
        self._task: asyncio.Task[None] | None = None

    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        self._registry.subscribe(event_type, handler)

    async def start(self) -> None:
        self._client = redis.from_url(self._cfg.url, decode_responses=True)
        if self._registry.has_handlers():
            try:
                await self._client.xgroup_create(self._cfg.stream, self._cfg.consumer_group, id="$", mkstream=True)
            except ResponseError as exc:
                if "BUSYGROUP" not in str(exc):
                    raise
            self._task = asyncio.create_task(self._consume(), name="redis-event-consumer")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        if self._client:
            await self._client.aclose()

    async def publish(self, event: Event) -> None:
        assert self._client, "bus not started"
        await self._client.xadd(
            self._cfg.stream, {"data": serialize(event)}, maxlen=self._cfg.stream_maxlen, approximate=True
        )

    async def _consume(self) -> None:
        assert self._client
        while True:
            response = cast(
                list[Any],
                await self._client.xreadgroup(
                    self._cfg.consumer_group,
                    self._cfg.consumer_name,
                    {self._cfg.stream: ">"},
                    count=50,
                    block=self._block_ms,
                ),
            )
            for _stream, messages in response or []:
                for message_id, fields in messages:
                    await self._handle(message_id, fields["data"])

    async def _handle(self, message_id: str, raw: str) -> None:
        assert self._client
        event = deserialize(raw)
        ok = True if event.is_none() else await dispatch_with_retry(self._registry, event.value)
        if event.is_none():
            log.warning("skipping unknown event %s", message_id)
        if ok:
            await self._client.xack(self._cfg.stream, self._cfg.consumer_group, message_id)
        # else: stays pending -> reclaim with XAUTOCLAIM or move to a dead-letter stream
