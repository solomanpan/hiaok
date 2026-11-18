"""Entity ids: random normally, deterministic while a write request is being executed.

A consumer may receive the same write request twice (at-least-once). With ids derived from the request id a
redelivery re-creates the same uuids, and the API can return the new entity's uuid *before* it exists.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from hiaok_core.facade import uuid_hex

_NAMESPACE = uuid.UUID("6f1d3c52-8a0b-4c8e-9a52-0d1f6b7e4a11")
_sequence: ContextVar[Iterator[str] | None] = ContextVar("command_id_sequence", default=None)


def _derived(request_id: str) -> Iterator[str]:
    n = 0
    while True:
        yield uuid.uuid5(_NAMESPACE, f"{request_id}:{n}").hex
        n += 1


def command_uuid(request_id: str) -> str:
    """The uuid of the FIRST entity created while executing ``request_id`` (the one the API reports back)."""
    return next(_derived(request_id))


@contextmanager
def deterministic_ids(request_id: str) -> Generator[None]:
    token = _sequence.set(_derived(request_id))
    try:
        yield
    finally:
        _sequence.reset(token)


def next_id() -> str:
    """Default ``IdGenerator`` of every application service."""
    sequence = _sequence.get()
    return next(sequence) if sequence is not None else uuid_hex()
