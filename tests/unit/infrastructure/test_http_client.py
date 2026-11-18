import httpx
import pytest
from hiaok_core.context import request_context
from hiaok_core.exception import HttpClientError
from hiaok_core.facade import HttpClient

from src.infrastructure.http import HttpxHttpClient


def _client(handler) -> HttpxHttpClient:
    return HttpxHttpClient("https://upstream.test", transport=httpx.MockTransport(handler))


async def test_implements_the_core_facade_and_propagates_request_id():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["request_id"] = request.headers["x-request-id"]
        seen["body"] = request.content
        return httpx.Response(201, json={"ok": True})

    client = _client(handler)
    assert isinstance(client, HttpClient)
    await client.start()
    try:
        with request_context(trace_id="trace-123"):
            resp = await client.post("/things", json_body={"name": "x"})
    finally:
        await client.stop()

    assert resp.status == 201 and resp.json() == {"ok": True}
    assert seen == {"request_id": "trace-123", "body": b'{"name":"x"}'}


async def test_transport_errors_become_http_client_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = _client(handler)
    await client.start()
    try:
        with pytest.raises(HttpClientError):
            await client.get("/down")
    finally:
        await client.stop()
