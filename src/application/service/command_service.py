"""Executes one accepted write request exactly once (idempotent) and records its outcome in ``sys_log``.

    execute(...)        @master: [already done?] -> run the usecase -> outcome row   (one transaction)
    record_failure(...) @master: outcome row for a rejected request (the first transaction was rolled back)

Outcome rows use ``log_type = command`` and ``log_uuid`` derived from the request id, so the API can look an
outcome up by ``requestId`` and a redelivered message finds the row and does nothing.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from expression import Error, Ok, Result
from hiaok_core.context import request_context
from hiaok_core.exception import DomainError
from hiaok_core.facade import TransactionManager

from ...domain.entity import SysLog
from ...domain.entity.event import WriteRequested
from ...domain.enum import LogType
from ..model.command import FAILED, SUCCESS
from .datasource import master
from .ids import deterministic_ids
from .sys_log_service import SysLogService


def command_log_uuid(request_id: str) -> str:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"hiaok:command:{request_id}").hex


def _outcome_row(command: WriteRequested, content: dict[str, Any]) -> SysLog:
    return SysLog(
        org_uuid=command.org_uuid,
        log_uuid=command_log_uuid(command.request_id),
        log_type=LogType.COMMAND,
        event_type=command.command_type,
        aggregate_id=command.target_uuid,
        trace_id=command.request_id,
        content={"request_id": command.request_id, "operator": command.operator, **content},
    )


class CommandService:
    def __init__(self, tx: TransactionManager, logs: SysLogService) -> None:
        self._tx = tx
        self._logs = logs

    @property
    def tx(self) -> TransactionManager:
        return self._tx

    @master
    async def execute(
        self, command: WriteRequested, run: Callable[[], Awaitable[Result[Any, DomainError]]]
    ) -> Result[None, DomainError]:
        """``Error`` => the whole transaction (including whatever ``run`` wrote) is rolled back."""
        if (await self._logs.find(command.org_uuid, command_log_uuid(command.request_id))).is_some():
            return Ok(None)  # redelivery of a request that already has an outcome
        with request_context(operator=command.operator, trace_id=command.request_id):
            with deterministic_ids(command.request_id):
                result = await run()
            if isinstance(result, Error):
                return Error(result.error)
            await self._logs.append(_outcome_row(command, {"status": SUCCESS}))
        return Ok(None)

    @master
    async def record_failure(self, command: WriteRequested, error: DomainError) -> None:
        content = {"status": FAILED, "kind": error.kind, "error_code": error.code, "msg": error.message}
        with request_context(operator=command.operator, trace_id=command.request_id):
            await self._logs.append(_outcome_row(command, content))
