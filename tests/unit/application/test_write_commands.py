"""Asynchronous writes: submit -> (bus) -> consume -> usecase -> outcome row, idempotent and rollback-safe."""

from __future__ import annotations

from datetime import date
from typing import Any, cast

import pytest
from expression import Error, Ok, Option, Result, option
from hiaok_core.context import request_context
from hiaok_core.exception import DomainError, conflict
from support import FakeTransactionManager, of_type

from src.application.model import (
    CreateRole,
    ResignPayload,
    RoleAssignmentModel,
    RolesPayload,
    UpdateUser,
    UserDetailModel,
    from_payload,
    to_payload,
)
from src.application.service import CommandService, SysLogService, command_uuid, next_id
from src.application.usecase.command import (
    CommandHandler,
    WriteSubmitter,
    command_outcome,
    typed,
    untyped,
    write_handler,
)
from src.domain.entity import SysLog
from src.domain.entity.event import WriteRequested
from src.domain.enum import RoleType
from src.infrastructure.messaging.in_memory import InMemoryEventBus


class FakeSysLogRepository:
    def __init__(self) -> None:
        self.rows: dict[str, SysLog] = {}

    async def append(self, log: SysLog) -> None:
        self.rows.setdefault(log.log_uuid, log)

    async def get(self, org_uuid: str, log_uuid: str) -> Option[SysLog]:
        return option.of_obj(self.rows.get(log_uuid))


class Harness:
    def __init__(self, handlers: dict[str, CommandHandler]) -> None:
        self.tx = FakeTransactionManager()
        self.repo = FakeSysLogRepository()
        self.logs = SysLogService(self.tx, cast(Any, self.repo))
        self.bus = InMemoryEventBus()
        self.submitter = WriteSubmitter(self.bus)
        self.bus.subscribe(WriteRequested, write_handler(CommandService(self.tx, self.logs), handlers))

    async def outcome(self, request_id: str):
        return await command_outcome(self.logs, "org-1", request_id)


def _calls() -> tuple[list[tuple[Any, ...]], CommandHandler]:
    calls: list[tuple[Any, ...]] = []

    async def create_role(command: WriteRequested) -> Result[Any, DomainError]:
        calls.append((command.command_type, command.target_uuid, next_id(), next_id()))
        return Ok(None)

    return calls, create_role


async def test_create_returns_a_derived_uuid_and_runs_the_usecase_with_it():
    calls, handler = _calls()
    h = Harness({"Role.create": handler})

    with request_context(operator="alice", trace_id=None):
        accepted = await h.submitter.create(
            "Role", "req-1", "org-1", CreateRole(org_uuid="org-1", tenant_uuid="t", role_code="R", role_name="n")
        )

    assert accepted.uuid == command_uuid("req-1") and accepted.status == "accepted"
    command = of_type(h.bus.published[0], WriteRequested)
    assert (command.command_type, command.operator, command.target_uuid) == ("Role.create", "alice", accepted.uuid)
    # the usecase saw the same first id the API reported; later ids are deterministic too
    assert calls == [("Role.create", accepted.uuid, accepted.uuid, calls[0][3])]
    assert h.tx.commits == 1 and h.tx.rollbacks == 0  # one transaction: usecase + outcome row
    assert (await h.outcome("req-1")).status == "success"


async def test_business_failure_rolls_back_and_is_recorded_not_retried():
    attempts = 0

    async def duplicate(_command: WriteRequested) -> Result[Any, DomainError]:
        nonlocal attempts
        attempts += 1
        return Error(conflict("duplicate_code", "role code 'R' already exists"))

    h = Harness({"Role.create": duplicate})
    await h.submitter.create(
        "Role", "req-2", "org-1", CreateRole(org_uuid="org-1", tenant_uuid="t", role_code="R", role_name="n")
    )

    outcome = await h.outcome("req-2")
    assert (outcome.status, outcome.kind, outcome.error_code) == ("failed", "conflict", "duplicate_code")
    assert outcome.msg == "role code 'R' already exists"
    assert attempts == 1
    assert h.tx.rollbacks == 1  # the usecase's own writes are rolled back; only the failure row is kept


async def test_redelivery_does_not_execute_twice():
    calls, handler = _calls()
    h = Harness({"Role.create": handler})
    await h.submitter.create(
        "Role", "req-3", "org-1", CreateRole(org_uuid="org-1", tenant_uuid="t", role_code="R", role_name="n")
    )
    await h.bus.publish(h.bus.published[0])  # the broker delivers the same message again

    assert len(calls) == 1


async def test_unknown_command_and_malformed_payload_are_recorded_as_failures():
    async def never(_c: WriteRequested, _m: ResignPayload) -> Result[Any, DomainError]:
        raise AssertionError("must not run")

    h = Harness({"Employee.resign": typed(ResignPayload, never)})
    await h.submitter.act("Employee", "fly", "req-4", "org-1", "e1")
    await h.submitter.act("Employee", "resign", "req-5", "org-1", "e1", RolesPayload())  # wrong shape

    assert (await h.outcome("req-4")).error_code == "unknown_command"
    assert (await h.outcome("req-5")).error_code == "invalid_payload"


async def test_outcome_is_pending_until_something_is_recorded():
    h = Harness({})
    outcome = await h.outcome("never-submitted")
    assert (outcome.status, outcome.command_type) == ("pending", None)


async def test_an_exception_is_not_swallowed_so_the_bus_can_retry_and_dead_letter():
    async def boom(_command: WriteRequested) -> Result[Any, DomainError]:
        raise RuntimeError("db down")

    h = Harness({"Role.delete": untyped(boom)})
    with pytest.raises(RuntimeError):
        await h.submitter.delete("Role", "req-6", "org-1", "r1")
    assert (await h.outcome("req-6")).status == "pending"


def test_payloads_round_trip_through_json():
    update = UpdateUser(email="a@b.c", detail=UserDetailModel(nickname="al", real_name=None))
    assert from_payload(UpdateUser, to_payload(update)) == update

    roles = RolesPayload((RoleAssignmentModel("r1", "p1"), RoleAssignmentModel("r2")))
    assert from_payload(RolesPayload, to_payload(roles)) == roles

    assert from_payload(ResignPayload, to_payload(ResignPayload(date(2026, 12, 31)))).leave_date == date(2026, 12, 31)

    create = CreateRole(org_uuid="o", tenant_uuid="t", role_code="R", role_name="n", role_type=RoleType.SYSTEM)
    assert from_payload(CreateRole, to_payload(create)) == create


def test_ids_are_random_outside_a_request_and_derived_inside():
    assert next_id() != next_id()
    assert command_uuid("a") == command_uuid("a") != command_uuid("b")
