"""``hiaok_core.facade.HttpClient`` implemented with httpx (async, one pooled client per process)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from hiaok_core.context import current_context
from hiaok_core.exception import HttpClientError
from hiaok_core.facade import HttpResponse


class HttpxHttpClient:
    """Propagates ``X-Request-Id`` from the current request context; transport errors -> ``HttpClientError``."""

    def __init__(
        self,
        base_url: str = "",
        *,
        timeout: float = 10.0,
        headers: Mapping[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,  # tests: httpx.MockTransport
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._headers = dict(headers or {})
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    async def start(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=self._base_url, timeout=self._timeout, headers=self._headers, transport=self._transport
        )

    async def stop(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def request(
        self,
        method: str,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        json_body: Any = None,
        headers: Mapping[str, str] | None = None,
        request_timeout: float | None = None,
    ) -> HttpResponse:
        if self._client is None:
            raise HttpClientError("HttpxHttpClient.start() was not called", url=url)
        merged = {"x-request-id": current_context().trace_id, **(headers or {})}
        try:
            resp = await self._client.request(
                method,
                url,
                params=params,
                json=json_body,
                headers=merged,
                timeout=request_timeout if request_timeout is not None else self._timeout,
            )
        except httpx.HTTPError as exc:
            raise HttpClientError(f"{method} {url} failed: {exc}", url=url) from exc
        return HttpResponse(status=resp.status_code, body=resp.content, headers=dict(resp.headers))

    async def get(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> HttpResponse:
        return await self.request("POST", url, **kwargs)
