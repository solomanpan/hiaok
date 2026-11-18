"""Building the OpenAPI document renders every request/response model: a cheap guard against broken schemas."""

import pytest
from fastapi.testclient import TestClient

from src.application.config import AppConfig, Settings
from src.main import create_app


def _app(**app_cfg):
    return create_app(Settings(app=AppConfig(broker="memory", cache="memory", **app_cfg)))


@pytest.fixture(scope="module")
def spec() -> dict:
    return _app().openapi()


def test_every_route_tagged_and_tag_documented(spec):
    declared = {t["name"] for t in spec["tags"]}
    used = {tag for path in spec["paths"].values() for op in path.values() for tag in op["tags"]}
    assert used <= declared, used - declared


def test_operation_ids_are_short_and_unique(spec):
    ids = [op["operationId"] for path in spec["paths"].values() for op in path.values()]
    assert len(ids) == len(set(ids))
    assert "role-create_role" in ids


def test_api_routes_document_domain_errors_and_context_headers(spec):
    op = spec["paths"]["/api/v1/orgs/{org_uuid}/roles/{role_uuid}"]["get"]
    assert {"403", "404", "409"} <= set(op["responses"])
    assert op["responses"]["404"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorEnvelope")
    headers = {p["name"] for p in op["parameters"] if p["in"] == "header"}
    assert headers == {"x-operator", "x-request-id"}


def test_swagger_ui_served():
    client = TestClient(_app())  # no `with`: lifespan (DB, broker) is not started
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "hiaok"


def test_docs_can_be_disabled():
    client = TestClient(_app(docs_enabled=False))
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
