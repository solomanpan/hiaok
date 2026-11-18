from __future__ import annotations

import asyncio
import contextlib
import logging

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from aiokafka.admin import AIOKafkaAdminClient, NewTopic
from aiokafka.errors import TopicAlreadyExistsError
from hiaok_core.facade import Event, EventHandler

from ...application.config import KafkaConfig
from .registry import HandlerRegistry, dispatch_with_retry
from .serde import deserialize, require_domain_event, serialize
from .topics import Topic, topic_of

log = logging.getLogger(__name__)


class KafkaEventBus:
    """Five domain topics (see ``topics.py``), one consumer per topic, key = aggregate id.

    Consume: handle -> retry -> still failing => copy to ``<topic>.dlq`` -> commit the offset. A message is only
    committed after it was handled or dead-lettered, so nothing is lost and one poison message never blocks a topic.
    """

    def __init__(self, config: KafkaConfig) -> None:
        self._cfg = config
        self._registry = HandlerRegistry()
        self._producer: AIOKafkaProducer | None = None
        self._consumers: dict[Topic, AIOKafkaConsumer] = {}
        self._tasks: list[asyncio.Task[None]] = []

    # ---------------------------------------------------------------- names
    def topic_name(self, topic: Topic) -> str:
        return f"{self._cfg.topic_prefix}.{topic.value}"

    def dlq_name(self, topic: Topic) -> str:
        return self.topic_name(topic) + self._cfg.dlq_suffix

    def group_name(self, topic: Topic) -> str:
        return f"{self._cfg.group_id}.{topic.value}"

    # ---------------------------------------------------------------- lifecycle
    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        self._registry.subscribe(event_type, handler)

    async def start(self) -> None:
        if self._cfg.create_topics:
            await self._create_topics()
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._cfg.bootstrap_servers, acks="all", enable_idempotence=True
        )
        await self._producer.start()
        if self._registry.has_handlers():
            for topic in Topic:
                consumer = AIOKafkaConsumer(
                    self.topic_name(topic),
                    bootstrap_servers=self._cfg.bootstrap_servers,
                    group_id=self.group_name(topic),
                    enable_auto_commit=False,
                    auto_offset_reset="earliest",
                )
                await consumer.start()
                self._consumers[topic] = consumer
                task = asyncio.create_task(self._consume(topic, consumer), name=f"kafka-consumer-{topic.value}")
                task.add_done_callback(self._log_crash)
                self._tasks.append(task)

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await task
        for consumer in self._consumers.values():
            await consumer.stop()
        if self._producer:
            await self._producer.stop()

    async def _create_topics(self) -> None:
        admin = AIOKafkaAdminClient(bootstrap_servers=self._cfg.bootstrap_servers)
        await admin.start()
        try:
            names = [n for t in Topic for n in (self.topic_name(t), self.dlq_name(t))]
            new = [
                NewTopic(name, num_partitions=self._cfg.num_partitions, replication_factor=self._cfg.replication_factor)
                for name in names
            ]
            with contextlib.suppress(TopicAlreadyExistsError):
                await admin.create_topics(new)
        finally:
            await admin.close()

    # ---------------------------------------------------------------- publish
    async def publish(self, event: Event) -> None:
        assert self._producer, "bus not started"
        domain_event = require_domain_event(event)
        await self._producer.send_and_wait(
            self.topic_name(topic_of(domain_event)),
            value=serialize(event).encode(),
            key=domain_event.aggregate_id.encode(),
            headers=[("event_type", event.event_type().encode())],
        )

    # ---------------------------------------------------------------- consume
    async def _consume(self, topic: Topic, consumer: AIOKafkaConsumer) -> None:
        async for message in consumer:
            if message.value is not None and not await self._handle(message):
                await self._dead_letter(topic, message)
            await consumer.commit()

    async def _handle(self, message: ConsumerRecord[bytes, bytes]) -> bool:
        """True when handled (or ignorable); False when it must go to the dead-letter topic."""
        assert message.value is not None
        try:
            event = deserialize(message.value)
        except Exception:
            log.exception("undecodable message at %s[%s]@%s", message.topic, message.partition, message.offset)
            return False
        if event.is_none():  # an event type this version does not know (produced by a newer release)
            return True
        return await dispatch_with_retry(self._registry, event.value)

    async def _dead_letter(self, topic: Topic, message: ConsumerRecord[bytes, bytes]) -> None:
        assert self._producer
        log.error("dead-lettering %s[%s]@%s", message.topic, message.partition, message.offset)
        headers = [
            *message.headers,
            ("source_topic", message.topic.encode()),
            ("source_partition", str(message.partition).encode()),
            ("source_offset", str(message.offset).encode()),
        ]
        await self._producer.send_and_wait(self.dlq_name(topic), value=message.value, key=message.key, headers=headers)

    @staticmethod
    def _log_crash(task: asyncio.Task[None]) -> None:
        if not task.cancelled() and task.exception() is not None:
            log.error("%s crashed", task.get_name(), exc_info=task.exception())
