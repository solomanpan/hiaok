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


def _operations(spec):
    return [(path, op) for path, item in spec["paths"].items() if path != "/health" for op in item.values()]


def test_every_api_is_post_under_the_versioned_prefix(spec):
    for path, item in spec["paths"].items():
        if path == "/health":
            continue
        assert path.startswith("/v1/api/hiaok/"), path
        assert set(item) == {"post"}, path


def test_every_api_takes_an_api_request_and_returns_an_api_response(spec):
    for path, op in _operations(spec):
        body = op["requestBody"]["content"]["application/json"]["schema"]["$ref"]
        assert body.rsplit("/", 1)[-1].startswith("ApiRequest_"), path
        ok = op["responses"]["200"]["content"]["application/json"]["schema"]["$ref"]
        assert ok.rsplit("/", 1)[-1].startswith("ApiResponse_"), path


def test_envelope_and_dto_fields_are_camel_case(spec):
    schemas = spec["components"]["schemas"]
    request = next(v for k, v in schemas.items() if k.startswith("ApiRequest_"))
    assert set(request["properties"]) == {"requestId", "reqInfo"}
    response = next(v for k, v in schemas.items() if k.startswith("ApiResponse_"))
    assert {"code", "msg", "resultInfo"} <= set(response["properties"])
    for name, schema in schemas.items():
        for field in schema.get("properties", {}):
            assert "_" not in field, (name, field)


def test_context_headers_are_documented(spec):
    op = spec["paths"]["/v1/api/hiaok/role/get"]["post"]
    headers = {p["name"] for p in op["parameters"] if p["in"] == "header"}
    assert headers == {"x-operator", "x-request-id", "authorization"}


def test_swagger_ui_served():
    client = TestClient(_app())  # no `with`: lifespan (DB, broker) is not started
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").json()["info"]["title"] == "hiaok"


def test_docs_can_be_disabled():
    client = TestClient(_app(docs_enabled=False))
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
