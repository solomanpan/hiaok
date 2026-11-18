from typing import cast

from src.application.service import SysLogService, config_cache_key
from src.application.usecase.event_handler import event_content, subscribe_event_handlers
from src.domain.entity import SysLog
from src.domain.entity.event import EntityCreated, RolePermissionsChanged, SysConfigChanged


class FakeSysLogService:
    """Stands in for SysLogService (which needs Postgres)."""

    def __init__(self) -> None:
        self.rows: list[SysLog] = []

    async def append(self, log: SysLog) -> None:
        self.rows.append(log)


def _config_changed() -> SysConfigChanged:
    return SysConfigChanged(org_uuid="o1", config_key="security.min_length", config_value="12")


async def test_every_event_is_audited_with_replay_safe_id(bus, cache):
    logs = FakeSysLogService()
    subscribe_event_handlers(bus, cast(SysLogService, logs), cache)

    event = EntityCreated(org_uuid="o1", entity_type="Role", entity_uuid="r1")
    await bus.publish(event)
    await bus.publish(event)  # at-least-once redelivery

    assert len(logs.rows) == 2
    assert logs.rows[0].log_uuid == logs.rows[1].log_uuid


async def test_sys_config_changed_evicts_cache(bus, cache):
    subscribe_event_handlers(bus, cast(SysLogService, FakeSysLogService()), cache)
    event = _config_changed()
    key = config_cache_key(event.org_uuid, event.config_key)
    await cache.set(key, "8")

    await bus.publish(event)

    assert (await cache.get(key)).is_none()


def test_event_content_drops_base_fields():
    event = RolePermissionsChanged(org_uuid="o1", role_uuid="r1", permission_uuids=("p1",))
    content = event_content(event)
    assert content["event_id"] == event.event_id
    assert content["permission_uuids"] == ["p1"]
    assert "org_uuid" not in content and "occurred_at" not in content
