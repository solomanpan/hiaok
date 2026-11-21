"""``hiaok bootstrap``: organization + administrator in one transaction, rolled back on any failure."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from expression import Error, Ok
from hiaok_core.factory import ErrorSpec
from support import FakeTransactionManager, err, ok

from src.application.model import CreateOrganization, RegisterUser
from src.bootstrap import Bootstrapped, bootstrap

PROVISIONED: Any = SimpleNamespace(
    organization=SimpleNamespace(org_uuid="o1"),
    tenant=SimpleNamespace(tenant_uuid="t1"),
    admin_role=SimpleNamespace(role_uuid="r1"),
)
FAILED = ErrorSpec.validation("boom", "boom")


async def _run(tx: FakeTransactionManager, provision: Any, register: Any):
    return await bootstrap(
        tx, provision, register, org_code="ACME", org_name="Acme", username="admin", password="secret-123"
    )


async def test_provisions_then_registers_the_administrator_with_the_admin_role():
    tx = FakeTransactionManager()
    seen: dict[str, Any] = {}

    async def provision(cmd: CreateOrganization):
        seen["org"] = cmd
        return Ok(PROVISIONED)

    async def register(cmd: RegisterUser):
        seen["user"] = cmd
        return Ok(SimpleNamespace(user_uuid="u1"))

    result = ok(await _run(tx, provision, register))

    assert result == Bootstrapped("o1", "t1", "r1", "u1", "admin")
    assert (seen["org"].org_code, seen["org"].org_name) == ("ACME", "Acme")
    user: RegisterUser = seen["user"]
    assert (user.org_uuid, user.tenant_uuid, user.username, user.role_uuids) == ("o1", "t1", "admin", ("r1",))
    assert (tx.commits, tx.rollbacks) == (1, 0)


async def test_a_failed_registration_rolls_back_the_organization():
    tx = FakeTransactionManager()

    async def provision(_: CreateOrganization):
        return Ok(PROVISIONED)

    async def register(_: RegisterUser):
        return Error(FAILED())

    assert err(await _run(tx, provision, register)).code == "boom"
    assert (tx.commits, tx.rollbacks) == (0, 1)


async def test_a_failed_provisioning_registers_nobody():
    tx = FakeTransactionManager()
    calls: list[RegisterUser] = []

    async def provision(_: CreateOrganization):
        return Error(FAILED())

    async def register(cmd: RegisterUser):
        calls.append(cmd)
        return Ok(SimpleNamespace(user_uuid="u1"))

    assert err(await _run(tx, provision, register)).code == "boom"
    assert calls == []
    assert tx.rollbacks == 1
