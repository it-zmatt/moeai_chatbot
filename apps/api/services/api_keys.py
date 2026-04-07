from __future__ import annotations

from datetime import datetime, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.api_key import ApiKey
from models.client import Client

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_api_key(api_key: str) -> str:
    return pwd_context.hash(api_key)


def verify_api_key(api_key: str, key_hash: str) -> bool:
    return pwd_context.verify(api_key, key_hash)


async def resolve_client_from_api_key(
    session: AsyncSession,
    api_key: str,
) -> Client | None:
    result = await session.execute(
        select(ApiKey, Client)
        .join(Client, ApiKey.client_id == Client.id)
        .where(ApiKey.is_active.is_(True), Client.is_active.is_(True))
    )

    for api_key_row, client in result.all():
        try:
            if verify_api_key(api_key, api_key_row.key_hash):
                api_key_row.last_used_at = datetime.now(timezone.utc)
                await session.commit()
                return client
        except Exception:
            continue

    return None
