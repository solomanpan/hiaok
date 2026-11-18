"""Asynchronous writes.

API side      ``WriteSubmitter.create / update / delete / act``   -> publish ``WriteRequested`` -> ``Accepted``
Consumer side ``handle_write(commands, handlers)``                -> run the matching usecase, record the outcome
Query side    ``command_outcome(logs)(org_uuid, request_id)``     -> ``CommandOutcome``

Handlers are keyed by ``command_type`` = ``<EntityType>.<action>`` (``Role.create``, ``Role.grant_permissions``).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from expression import Error, Result
from hiaok_core.context import current_context
from hiaok_core.exception import DomainError
from hiaok_core.facade import EventHandler, EventPublisher
from hiaok_core.fp import curry
from pydantic import ValidationError

from ...domain.entity.event import WriteRequested
from ..model.command import (
    FAILED,
    PENDING,
    Accepted,
    CommandOutcome,
    from_payload,
    to_payload,
)
from ..service import CommandService, SysLogService, command_log_uuid, command_uuid
from .errors import UseCaseErrors

type CommandHandler = Callable[[WriteRequested], Awaitable[Result[Any, DomainError]]]


# ---------------------------------------------------------------- handlers
def typed[M](model_type: type[M], call: Callable[[WriteRequested, M], Awaitable[Result[Any, DomainError]]]):
    """Handler whose payload is ``model_type`` (parsed here; a malformed payload is a *failed request*, not a crash)."""

    async def run(command: WriteRequested) -> Result[Any, DomainError]:
        try:
            model = from_payload(model_type, command.payload)
        except ValidationError as e:
            return UseCaseErrors.invalid_payload.err(command_type=command.command_type, problem=e.errors()[0]["msg"])
        return await call(command, model)

    return run


def untyped(call: Callable[[WriteRequested], Awaitable[Result[Any, DomainError]]]):
    """Handler without a payload (delete)."""
    return call


@curry
async def handle_write(commands: CommandService, handlers: Mapping[str, CommandHandler], event: WriteRequested) -> None:
    """Consumer for ``WriteRequested``. Business failures are recorded (and NOT retried); exceptions propagate so
    the bus retries and finally dead-letters the message."""
    handler = handlers.get(event.command_type)
    if handler is None:
        await commands.record_failure(event, UseCaseErrors.unknown_command(command_type=event.command_type))
        return
    result = await commands.execute(event, lambda: handler(event))
    if isinstance(result, Error):
        await commands.record_failure(event, result.error)


def write_handler(commands: CommandService, handlers: Mapping[str, CommandHandler]) -> EventHandler[WriteRequested]:
    return handle_write(commands, handlers)


# ---------------------------------------------------------------- submit (API side)
class WriteSubmitter:
    def __init__(self, publisher: EventPublisher) -> None:
        self._publisher = publisher

    async def create(self, entity: str, request_id: str, org_uuid: str | None, payload: object) -> Accepted:
        """The new entity's uuid is derived from the request id, so it can be returned before it exists."""
        new_uuid = command_uuid(request_id)
        return await self._submit(entity, "create", request_id, org_uuid or new_uuid, new_uuid, payload)

    async def update(self, entity: str, request_id: str, org_uuid: str, uuid: str, payload: object) -> Accepted:
        return await self._submit(entity, "update", request_id, org_uuid, uuid, payload)

    async def delete(self, entity: str, request_id: str, org_uuid: str, uuid: str) -> Accepted:
        return await self._submit(entity, "delete", request_id, org_uuid, uuid, None)

    async def act(
        self, entity: str, action: str, request_id: str, org_uuid: str, uuid: str, payload: object | None = None
    ) -> Accepted:
        return await self._submit(entity, action, request_id, org_uuid, uuid, payload)

    async def _submit(
        self, entity: str, action: str, request_id: str, org_uuid: str, target_uuid: str, payload: object | None
    ) -> Accepted:
        await self._publisher.publish(
            WriteRequested(
                org_uuid=org_uuid,
                request_id=request_id,
                entity_type=entity,
                command_type=f"{entity}.{action}",
                target_uuid=target_uuid,
                operator=current_context().operator,
                payload={} if payload is None else to_payload(payload),
            )
        )
        return Accepted(request_id=request_id, uuid=target_uuid)


# ---------------------------------------------------------------- outcome (query side)
@curry
async def command_outcome(logs: SysLogService, org_uuid: str, request_id: str) -> CommandOutcome:
    """``pending`` = no outcome recorded: not consumed yet, still being retried, or dead-lettered."""
    found = await logs.find(org_uuid, command_log_uuid(request_id))
    if found.is_none():
        return CommandOutcome(request_id=request_id, status=PENDING)
    row = found.value
    content = row.content
    return CommandOutcome(
        request_id=request_id,
        status=str(content.get("status", FAILED)),
        command_type=row.event_type,
        uuid=row.aggregate_id,
        kind=content.get("kind"),
        error_code=content.get("error_code"),
        msg=content.get("msg"),
    )
