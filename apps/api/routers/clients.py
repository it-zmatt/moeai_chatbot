from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from dependencies.auth import get_current_client
from models.client import Client
from schemas.clients import ClientCreate, ClientRead, ClientUpdate
from services.clients import (
    create_client_for_tenant,
    delete_client_for_tenant,
    get_client_for_tenant,
    list_clients_for_tenant,
    update_client_for_tenant,
)

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=list[ClientRead])
async def list_clients(
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> list[Client]:
    return await list_clients_for_tenant(db, current_client.tenant_id)


@router.get("/{client_id}", response_model=ClientRead)
async def get_client(
    client_id: UUID,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> Client:
    client = await get_client_for_tenant(db, current_client.tenant_id, client_id)
    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.post("", response_model=ClientRead, status_code=status.HTTP_201_CREATED)
async def create_client(
    body: ClientCreate,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> Client:
    try:
        return await create_client_for_tenant(
            db,
            current_client.tenant_id,
            body.model_dump(mode="json"),
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client with this slug already exists",
        ) from None


@router.patch("/{client_id}", response_model=ClientRead)
async def update_client(
    client_id: UUID,
    body: ClientUpdate,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> Client:
    try:
        client = await update_client_for_tenant(
            db,
            current_client.tenant_id,
            client_id,
            body.model_dump(exclude_unset=True, mode="json"),
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A client with this slug already exists",
        ) from None

    if client is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: UUID,
    current_client: Client = Depends(get_current_client),
    db: AsyncSession = Depends(get_session),
) -> Response:
    deleted = await delete_client_for_tenant(db, current_client.tenant_id, client_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
