from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from core.database import AsyncSessionLocal
from services.api_keys import resolve_client_from_api_key

PUBLIC_PATHS = {"/health", "/openapi.json", "/favicon.ico", "/api-keys/validate"}
PUBLIC_PATH_PREFIXES = ("/docs", "/redoc")


async def api_key_auth_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable],
):
    if (
        request.method == "OPTIONS"
        or request.url.path in PUBLIC_PATHS
        or request.url.path.startswith(PUBLIC_PATH_PREFIXES)
    ):
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Missing API key"},
        )

    async with AsyncSessionLocal() as session:
        current_client = await resolve_client_from_api_key(session, api_key)

    if current_client is None:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Invalid or inactive API key"},
        )

    request.state.current_client = current_client
    request.state.api_key = api_key
    return await call_next(request)
