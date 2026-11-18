"""Every asynchronous write the API accepts has a handler, and every handler is reachable from the API."""

import re
from pathlib import Path

from src.application.config import AppConfig, Settings
from src.infrastructure.resources import build_resources
from src.presentation.dependency import build_write_handlers

ENDPOINTS = Path(__file__).resolve().parents[3] / "src" / "presentation" / "endpoint"

_CRUD = re.compile(r'submitter\.(create|update|delete)\(\s*"(\w+)"')
_ACT = re.compile(r'submitter\.act\(\s*"(\w+)",\s*"(\w+)"')

# carry a clear-text password: executed synchronously, never put on a Kafka topic
SYNCHRONOUS = {"User.create", "Employee.create"}


def _submitted() -> set[str]:
    found: set[str] = set()
    for path in ENDPOINTS.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        found |= {f"{entity}.{action}" for action, entity in _CRUD.findall(text)}
        found |= {f"{entity}.{action}" for entity, action in _ACT.findall(text)}
    return found


def _handlers() -> set[str]:
    resources = build_resources(Settings(app=AppConfig(broker="memory", cache="memory")))
    return set(build_write_handlers(resources))


def test_every_submitted_command_has_a_handler():
    assert _submitted() - _handlers() == set()


def test_every_handler_is_submitted_by_some_endpoint():
    assert _handlers() - _submitted() == set()


def test_password_carrying_writes_stay_synchronous():
    assert not (_submitted() | _handlers()) & SYNCHRONOUS
