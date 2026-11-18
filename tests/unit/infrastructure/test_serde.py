import json

from support import of_type

from src.domain.entity.event import EntityUpdated, RolePermissionsChanged
from src.infrastructure.messaging.serde import deserialize, serialize


def test_roundtrip_keeps_tuples_and_datetime():
    event = RolePermissionsChanged(org_uuid="o1", role_uuid="r1", permission_uuids=("p1", "p2"))
    restored = deserialize(serialize(event))
    assert restored.is_some() and restored.value == event
    assert isinstance(of_type(restored.value, RolePermissionsChanged).permission_uuids, tuple)


def test_envelope_shape():
    raw = json.loads(serialize(EntityUpdated(org_uuid="o1", entity_type="Role", entity_uuid="r1")))
    assert raw["event_type"] == "EntityUpdated"
    assert raw["payload"]["entity_uuid"] == "r1"


def test_unknown_event_type_is_nothing():
    raw = json.dumps({"event_type": "Nope", "payload": {"occurred_at": "2026-01-01T00:00:00+00:00"}})
    assert deserialize(raw).is_none()
