from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.client import Client


async def list_clients_for_tenant(
    session: AsyncSession,
    tenant_id: UUID,
) -> list[Client]:
    result = await session.execute(
        select(Client)
        .where(Client.tenant_id == tenant_id)
        .order_by(Client.created_at.desc())
    )
    return list(result.scalars().all())


async def get_client_for_tenant(
    session: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
) -> Client | None:
    result = await session.execute(
        select(Client).where(Client.id == client_id, Client.tenant_id == tenant_id)
    )
    return result.scalar_one_or_none()


async def create_client_for_tenant(
    session: AsyncSession,
    tenant_id: UUID,
    payload: dict[str, Any],
) -> Client:
    client = Client(tenant_id=tenant_id, **payload)
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def update_client_for_tenant(
    session: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
    payload: dict[str, Any],
) -> Client | None:
    client = await get_client_for_tenant(session, tenant_id, client_id)
    if client is None:
        return None

    for field_name, value in payload.items():
        setattr(client, field_name, value)

    await session.commit()
    await session.refresh(client)
    return client


async def delete_client_for_tenant(
    session: AsyncSession,
    tenant_id: UUID,
    client_id: UUID,
) -> bool:
    client = await get_client_for_tenant(session, tenant_id, client_id)
    if client is None:
        return False

    await session.delete(client)
    await session.commit()
    return True
