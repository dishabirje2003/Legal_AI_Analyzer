from __future__ import annotations

import time
from typing import Any

import httpx
from supabase import Client, ClientOptions, create_client

from app.config import settings

# PostgREST's default httpx client uses http2=True; many concurrent requests on one
# connection can trigger RemoteProtocolError / ConnectionTerminated from the edge.
_RETRYABLE_HTTPS = (
    httpx.RemoteProtocolError,
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.ConnectTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)


def _make_supabase_httpx() -> httpx.Client:
    return httpx.Client(
        follow_redirects=True,
        http2=False,
        timeout=httpx.Timeout(connect=30.0, read=120.0, write=120.0, pool=30.0),
        limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
    )


def get_supabase_client() -> Client:
    options = ClientOptions(httpx_client=_make_supabase_httpx())
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
        options=options,
    )


def supabase_execute(request_builder: Any, *, max_attempts: int = 4) -> Any:
    """Run builder.execute() with retries on transient HTTP transport errors."""
    last: BaseException | None = None
    for attempt in range(max_attempts):
        try:
            return request_builder.execute()
        except _RETRYABLE_HTTPS as e:
            last = e
            if attempt < max_attempts - 1:
                time.sleep(0.15 * (2**attempt))
    assert last is not None
    raise last


supabase: Client = get_supabase_client()
