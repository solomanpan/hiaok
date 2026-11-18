"""Asynchronous writes: what the API accepts, what travels in the message, what the caller can look up later."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import TypeAdapter

from .user import RoleAssignmentModel

ACCEPTED = "accepted"
SUCCESS = "success"
FAILED = "failed"
PENDING = "pending"  # no outcome recorded (yet)


@dataclass(frozen=True)
class Accepted:
    """Returned by the API instead of the written entity."""

    request_id: str
    uuid: str  # new entity (create) or the target of the request
    status: str = ACCEPTED


@dataclass(frozen=True)
class CommandOutcome:
    request_id: str
    status: str
    command_type: str | None = None
    uuid: str | None = None
    kind: str | None = None  # DomainError.kind when failed
    error_code: str | None = None
    msg: str | None = None


# ---- payloads of the actions that are not plain create / update / delete
@dataclass(frozen=True)
class MovePayload:
    parent_uuid: str | None = None


@dataclass(frozen=True)
class AppointHeadPayload:
    employee_uuid: str | None = None


@dataclass(frozen=True)
class PermissionsPayload:
    permission_uuids: tuple[str, ...] = ()


@dataclass(frozen=True)
class MenusPayload:
    menu_uuids: tuple[str, ...] = ()


@dataclass(frozen=True)
class RolesPayload:
    roles: tuple[RoleAssignmentModel, ...] = ()


@dataclass(frozen=True)
class TransferPayload:
    department_uuid: str


@dataclass(frozen=True)
class ResignPayload:
    leave_date: date


def to_payload(model: object) -> dict[str, Any]:
    """Application command -> JSON-able dict (dates / enums / tuples included)."""
    return TypeAdapter(type(model)).dump_python(model, mode="json")


def from_payload[M](model_type: type[M], payload: dict[str, Any]) -> M:
    return TypeAdapter(model_type).validate_python(payload)
