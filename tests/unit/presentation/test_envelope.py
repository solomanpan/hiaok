"""Request/response envelope: requestId + reqInfo in, code + msg + resultInfo out, camelCase on the wire."""

import pytest
from expression import Error, Ok
from fastapi import FastAPI
from fastapi.testclient import TestClient
from hiaok_core.exception import conflict, forbidden, not_found, validation

from src.presentation.exception import install_exception_handlers
from src.presentation.schema.common import ApiModel, Keyed, OrgScoped
from src.presentation.schema.envelope import ApiRequest, ApiResponse, done, reply


class NoteRequest(OrgScoped):
    note_title: str


class NoteResponse(ApiModel):
    org_uuid: str
    note_title: str
    note_uuid: str


def _app(result) -> TestClient:
    app = FastAPI()
    install_exception_handlers(app)

    @app.post("/note/add")
    async def add(request: ApiRequest[NoteRequest]) -> ApiResponse[NoteResponse]:
        info = request.req_info
        return reply(
            result, lambda uuid: NoteResponse(org_uuid=info.org_uuid, note_title=info.note_title, note_uuid=uuid)
        )

    @app.post("/note/delete")
    async def delete(request: ApiRequest[Keyed]) -> ApiResponse[None]:
        return done(result)

    return TestClient(app)


REQUEST = {"requestId": "202612231234567", "reqInfo": {"orgUuid": "o1", "noteTitle": "hello"}}


def test_success_is_camel_case_and_has_no_error_code():
    r = _app(Ok("n1")).post("/note/add", json=REQUEST)
    assert r.status_code == 200
    assert r.json() == {
        "code": 0,
        "msg": "success",
        "resultInfo": {"orgUuid": "o1", "noteTitle": "hello", "noteUuid": "n1"},
    }


def test_command_without_payload_has_null_result():
    r = _app(Ok(None)).post("/note/delete", json={"requestId": "r1", "reqInfo": {"orgUuid": "o1", "uuid": "n1"}})
    assert r.json() == {"code": 0, "msg": "success", "resultInfo": None}


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (validation("bad", "m"), 400),
        (forbidden("no", "m"), 403),
        (not_found("Note", "n1"), 404),
        (conflict("dup", "m"), 409),
    ],
)
def test_domain_error_is_http_200_with_code_by_kind(error, code):
    r = _app(Error(error)).post("/note/add", json=REQUEST)
    assert r.status_code == 200
    payload = r.json()
    assert payload["code"] == code
    assert payload["errorCode"] == error.code
    assert payload["msg"] == error.message
    assert payload["resultInfo"] is None


@pytest.mark.parametrize(
    ("payload", "problem"),
    [
        ({"reqInfo": REQUEST["reqInfo"]}, "requestId"),
        ({"requestId": "r1"}, "reqInfo"),
        ({"requestId": "r1", "reqInfo": {"orgUuid": "o1"}}, "noteTitle"),
        ({"requestId": "", "reqInfo": REQUEST["reqInfo"]}, "requestId"),
    ],
)
def test_malformed_request_is_code_400(payload, problem):
    r = _app(Ok("n1")).post("/note/add", json=payload)
    assert r.status_code == 200
    result = r.json()
    assert (result["code"], result["errorCode"], result["resultInfo"]) == (400, "invalid_request", None)
    assert problem in result["msg"]


def test_snake_case_field_names_are_also_accepted_in_python():
    assert NoteRequest(org_uuid="o", note_title="t") == NoteRequest.model_validate({"orgUuid": "o", "noteTitle": "t"})
