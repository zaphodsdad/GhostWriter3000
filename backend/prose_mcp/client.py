"""HTTP client for proxying MCP tool calls to the local FastAPI app."""

from __future__ import annotations

import os
import logging

import httpx

logger = logging.getLogger("prose_mcp.client")

DEFAULT_TIMEOUT = httpx.Timeout(30.0, connect=5.0)
LONG_TIMEOUT = httpx.Timeout(120.0, connect=5.0)


class ProseClient:
    """Async HTTP client targeting the local prose-pipeline FastAPI app."""

    def __init__(self, base_url: str = "http://127.0.0.1:8000", api_key: str = ""):
        self.base_url = base_url
        self._api_key = api_key
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = {}
            if self._api_key:
                headers["X-API-Key"] = self._api_key
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=DEFAULT_TIMEOUT,
            )
        return self._client

    async def get(self, path: str, params: dict | None = None, timeout: httpx.Timeout | None = None) -> dict:
        client = await self._get_client()
        resp = await client.get(path, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, json: dict | None = None, timeout: httpx.Timeout | None = None) -> dict:
        client = await self._get_client()
        resp = await client.post(path, json=json, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    async def put(self, path: str, json: dict | None = None) -> dict:
        client = await self._get_client()
        resp = await client.put(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, path: str, params: dict | None = None) -> dict:
        client = await self._get_client()
        resp = await client.delete(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# -- Singleton access --

_client: ProseClient | None = None


def get_client() -> ProseClient:
    """Get or create the singleton ProseClient."""
    global _client
    if _client is None:
        port = os.getenv("PORT", "8000")
        api_key = os.getenv("API_AUTH_KEY", "")
        _client = ProseClient(
            base_url=f"http://127.0.0.1:{port}",
            api_key=api_key,
        )
    return _client


async def safe_get(path: str, **kwargs) -> dict:
    """GET with standardized error handling."""
    return await _safe_request(get_client().get(path, **kwargs))


async def safe_post(path: str, **kwargs) -> dict:
    """POST with standardized error handling."""
    return await _safe_request(get_client().post(path, **kwargs))


async def safe_put(path: str, **kwargs) -> dict:
    """PUT with standardized error handling."""
    return await _safe_request(get_client().put(path, **kwargs))


async def safe_delete(path: str, **kwargs) -> dict:
    """DELETE with standardized error handling."""
    return await _safe_request(get_client().delete(path, **kwargs))


async def _safe_request(coro) -> dict:
    """Execute an HTTP request with consistent error handling."""
    try:
        return await coro
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        try:
            detail = e.response.json().get("detail", e.response.text[:300])
        except Exception:
            detail = e.response.text[:300]
        raise RuntimeError(f"HTTP {status}: {detail}") from None
    except httpx.ConnectError:
        raise RuntimeError(
            "Cannot connect to prose-pipeline API. Is the server running?"
        ) from None
    except httpx.TimeoutException:
        raise RuntimeError(
            "Request timed out. The operation may still be in progress."
        ) from None
