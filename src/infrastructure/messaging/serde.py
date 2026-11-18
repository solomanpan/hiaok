"""JSON envelope ``{"event_type": "...", "payload": {...}}``."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime

from expression import Option
from hiaok_core import json
from hiaok_core.facade import Event

from ...domain.entity import event as _registers_every_event_class  # noqa: F401
from ...domain.entity.event import DomainEvent, event_class


def require_domain_event(event: Event) -> DomainEvent:
    """The bus facade accepts any ``Event``; only domain events have a wire format here."""
    if not isinstance(event, DomainEvent):
        raise TypeError(f"cannot publish {type(event).__name__}: only DomainEvent subclasses are serialisable")
    return event


def serialize(event: Event) -> str:
    domain_event = require_domain_event(event)
    return json.dumps({"event_type": domain_event.event_type(), "payload": asdict(domain_event)})


def deserialize(raw: str | bytes) -> Option[DomainEvent]:
    """``Nothing`` for unknown event types (e.g. produced by a newer service version)."""
    envelope = json.loads(raw)
    payload = dict(envelope["payload"])
    payload["occurred_at"] = datetime.fromisoformat(payload["occurred_at"])
    return event_class(envelope["event_type"]).map(lambda cls: cls(**payload))
