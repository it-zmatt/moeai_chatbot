from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from dependencies.auth import get_current_client
from models.client import Client
from schemas.api_key import (
    ApiKeyCreate,
    ApiKeyCreatedResponse,
    ApiKeyResponse,
    ApiKeyUpdate,
    ApiKeyValidateRequest,
    ApiKeyValidateResponse,
)
from services import api_key_service

# ---------------------------------------------------------------------------
# Two routers:
#   - keys_router  — scoped under /clients/{client_id}/api-keys
#   - validate_router — standalone at /api-keys/validate
# Both are registered in main.py
# ---------------------------------------------------------------------------

keys_router = APIRouter(prefix="/api-keys", tags=["api-keys"])
validate_router = APIRouter(prefix="/api-keys", tags=["api-keys"])


async def _require_client(
    db: AsyncSession,
    client_id: UUID,
    current_client: Client,
) -> Client:
    if client_id != current_client.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    client = await db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@keys_router.get("", response_model=list[ApiKeyResponse])
async def list_api_keys(
    client_id: UUID,
    active_only: bool = Query(default=False),
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> list[ApiKeyResponse]:
    await _require_client(db, client_id, current_client)
    return await api_key_service.list_api_keys(db, client_id, active_only=active_only)


@keys_router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    client_id: UUID,
    key_id: UUID,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyResponse:
    await _require_client(db, client_id, current_client)
    row = await api_key_service.get_api_key(db, client_id, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return row


@keys_router.post("", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    client_id: UUID,
    body: ApiKeyCreate,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyCreatedResponse:
    await _require_client(db, client_id, current_client)
    row, raw_key = await api_key_service.create_api_key(db, client_id, body.label)
    return ApiKeyCreatedResponse(
        id=row.id,
        client_id=row.client_id,
        label=row.label,
        is_active=row.is_active,
        last_used_at=row.last_used_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
        raw_key=raw_key,
    )


@keys_router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    client_id: UUID,
    key_id: UUID,
    body: ApiKeyUpdate,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyResponse:
    await _require_client(db, client_id, current_client)
    data = body.model_dump(exclude_unset=True)
    row = await api_key_service.update_api_key(db, client_id, key_id, data.get("label"))
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return row


@keys_router.delete("/{key_id}", response_model=ApiKeyResponse)
async def revoke_api_key(
    client_id: UUID,
    key_id: UUID,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyResponse:
    await _require_client(db, client_id, current_client)
    row = await api_key_service.revoke_api_key(db, client_id, key_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return row


@validate_router.post("/validate", response_model=ApiKeyValidateResponse)
async def validate_api_key(
    body: ApiKeyValidateRequest,
    db: AsyncSession = Depends(get_session),
) -> ApiKeyValidateResponse:
    row = await api_key_service.validate_api_key(db, body.raw_key)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or revoked API key",
        )
    return ApiKeyValidateResponse(valid=True, client_id=row.client_id, key_id=row.id)
