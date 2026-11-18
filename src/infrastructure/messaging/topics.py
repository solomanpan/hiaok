"""Which Kafka topic an event travels on: one topic per business domain.

    hiaok.organization   organization / tenant / project
    hiaok.identity       user / user group
    hiaok.authorization  role / permission / menu
    hiaok.hr             employee / department
    hiaok.config         system configuration

Each topic has its own consumer group and a dead-letter topic (``<topic>.dlq``). The key is the aggregate id,
so everything about one aggregate stays in order within its topic. Both the write requests (``WriteRequested``)
and the domain events they cause are routed here, by the entity they belong to.
"""

from __future__ import annotations

from enum import StrEnum

from ...domain.entity.event import (
    DepartmentHeadAppointed,
    DomainEvent,
    EmployeeLinkedToUser,
    EmployeeTransferred,
    EntityCreated,
    EntityDeleted,
    EntityUpdated,
    OrganizationProvisioned,
    RoleMenusChanged,
    RolePermissionsChanged,
    SysConfigChanged,
    UserPasswordChanged,
    UserRegistered,
    UserRolesAssigned,
    WriteRequested,
)


class Topic(StrEnum):
    ORGANIZATION = "organization"
    IDENTITY = "identity"
    AUTHORIZATION = "authorization"
    HR = "hr"
    CONFIG = "config"


TOPIC_OF_ENTITY: dict[str, Topic] = {
    "Organization": Topic.ORGANIZATION,
    "Tenant": Topic.ORGANIZATION,
    "Project": Topic.ORGANIZATION,
    "User": Topic.IDENTITY,
    "UserGroup": Topic.IDENTITY,
    "Role": Topic.AUTHORIZATION,
    "Permission": Topic.AUTHORIZATION,
    "Menu": Topic.AUTHORIZATION,
    "Employee": Topic.HR,
    "Department": Topic.HR,
    "SysConfig": Topic.CONFIG,
}

TOPIC_OF_EVENT: dict[type[DomainEvent], Topic] = {
    OrganizationProvisioned: Topic.ORGANIZATION,
    UserRegistered: Topic.IDENTITY,
    UserRolesAssigned: Topic.IDENTITY,
    UserPasswordChanged: Topic.IDENTITY,
    RolePermissionsChanged: Topic.AUTHORIZATION,
    RoleMenusChanged: Topic.AUTHORIZATION,
    DepartmentHeadAppointed: Topic.HR,
    EmployeeTransferred: Topic.HR,
    EmployeeLinkedToUser: Topic.HR,
    SysConfigChanged: Topic.CONFIG,
}


class UnroutableEvent(LookupError):
    """A new event or entity type was added without deciding which topic it belongs to."""


def topic_of(event: DomainEvent) -> Topic:
    if isinstance(event, EntityCreated | EntityUpdated | EntityDeleted | WriteRequested):
        topic = TOPIC_OF_ENTITY.get(event.entity_type)
    else:
        topic = TOPIC_OF_EVENT.get(type(event))
    if topic is None:
        raise UnroutableEvent(f"no topic for {event.event_type()} ({getattr(event, 'entity_type', '-')})")
    return topic
