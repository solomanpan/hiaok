"""Topic routing: every event and every aggregate must belong to exactly one of the five domain topics."""

import pytest

from src.domain.entity import AggregateRoot
from src.domain.entity.event import (
    EntityCreated,
    RoleMenusChanged,
    SysConfigChanged,
    UserPasswordChanged,
    WriteRequested,
    all_event_types,
)
from src.infrastructure.messaging.topics import (
    TOPIC_OF_ENTITY,
    TOPIC_OF_EVENT,
    Topic,
    UnroutableEvent,
    topic_of,
)


def _aggregates() -> set[str]:
    found: set[str] = set()
    stack = list(AggregateRoot.__subclasses__())
    while stack:
        cls = stack.pop()
        stack.extend(cls.__subclasses__())
        found.add(cls.entity_type())
    return found


def test_five_domain_topics():
    assert {t.value for t in Topic} == {"organization", "identity", "authorization", "hr", "config"}


def test_every_aggregate_has_a_topic():
    assert _aggregates() <= set(TOPIC_OF_ENTITY)


def test_every_business_event_has_a_topic():
    generic = {"EntityCreated", "EntityUpdated", "EntityDeleted", "WriteRequested"}
    business = {cls for cls in all_event_types() if cls.event_type() not in generic}
    assert business <= set(TOPIC_OF_EVENT)


@pytest.mark.parametrize(
    ("event", "topic"),
    [
        (EntityCreated(org_uuid="o", entity_type="Role", entity_uuid="r"), Topic.AUTHORIZATION),
        (EntityCreated(org_uuid="o", entity_type="Employee", entity_uuid="e"), Topic.HR),
        (UserPasswordChanged(org_uuid="o", user_uuid="u"), Topic.IDENTITY),
        (RoleMenusChanged(org_uuid="o", role_uuid="r", menu_uuids=()), Topic.AUTHORIZATION),
        (SysConfigChanged(org_uuid="o", config_key="k", config_value="v"), Topic.CONFIG),
    ],
)
def test_events_go_to_their_domain_topic(event, topic):
    assert topic_of(event) is topic


def test_a_write_request_goes_where_its_events_will_go():
    request = WriteRequested(
        org_uuid="o", request_id="r", entity_type="Tenant", command_type="Tenant.create", target_uuid="t", operator="x"
    )
    assert topic_of(request) is Topic.ORGANIZATION
    assert request.aggregate_id == "t"  # Kafka key: all requests for one aggregate stay in order


def test_unrouted_entity_is_an_error_not_a_silent_default():
    with pytest.raises(UnroutableEvent):
        topic_of(EntityCreated(org_uuid="o", entity_type="Mystery", entity_uuid="m"))
