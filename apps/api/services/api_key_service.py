"""
Service layer for API key lifecycle management.

Security rules:
- Raw keys are NEVER stored. Only the bcrypt hash lives in the DB.
- key_hash is NEVER returned from any function here (callers get ApiKey ORM rows
  and the schemas exclude key_hash from serialisation).
- validate_api_key scans all active keys for the given client and bcrypt-verifies
  the submitted raw key against each stored hash.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.api_key import ApiKey

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

KEY_PREFIX = "moe_"


def generate_raw_key() -> str:
    """Return a fresh, cryptographically random API key string."""
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(raw_key: str) -> str:
    """Return the bcrypt hash of *raw_key*."""
    return _pwd_ctx.hash(raw_key)


def verify_key(raw_key: str, key_hash: str) -> bool:
    """Return True when *raw_key* matches the stored *key_hash*."""
    return _pwd_ctx.verify(raw_key, key_hash)


# ---------------------------------------------------------------------------
# DB queries
# ---------------------------------------------------------------------------


async def list_api_keys(
    db: AsyncSession,
    client_id: uuid.UUID,
    *,
    active_only: bool = False,
) -> list[ApiKey]:
    stmt = select(ApiKey).where(ApiKey.client_id == client_id)
    if active_only:
        stmt = stmt.where(ApiKey.is_active.is_(True))
    stmt = stmt.order_by(ApiKey.created_at.asc())
    result = await db.scalars(stmt)
    return list(result.all())


async def get_api_key(
    db: AsyncSession,
    client_id: uuid.UUID,
    key_id: uuid.UUID,
) -> ApiKey | None:
    row = await db.get(ApiKey, key_id)
    if row is None or row.client_id != client_id:
        return None
    return row


async def create_api_key(
    db: AsyncSession,
    client_id: uuid.UUID,
    label: str | None,
) -> tuple[ApiKey, str]:
    """
    Generate a new API key, hash it, persist the hash, and return
    (ApiKey ORM row, raw_key). The raw_key must be returned to the caller
    and shown to the user exactly once — it is not stored anywhere.
    """
    raw_key = generate_raw_key()
    row = ApiKey(
        client_id=client_id,
        key_hash=hash_key(raw_key),
        label=label,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row, raw_key


async def update_api_key(
    db: AsyncSession,
    client_id: uuid.UUID,
    key_id: uuid.UUID,
    label: str | None,
) -> ApiKey | None:
    row = await get_api_key(db, client_id, key_id)
    if row is None:
        return None
    row.label = label
    await db.commit()
    await db.refresh(row)
    return row


async def revoke_api_key(
    db: AsyncSession,
    client_id: uuid.UUID,
    key_id: uuid.UUID,
) -> ApiKey | None:
    row = await get_api_key(db, client_id, key_id)
    if row is None:
        return None
    row.is_active = False
    await db.commit()
    await db.refresh(row)
    return row


async def validate_api_key(
    db: AsyncSession,
    raw_key: str,
) -> ApiKey | None:
    """
    Verify *raw_key* against all active stored hashes.
    Returns the matching ApiKey (with last_used_at updated) or None.

    Note: bcrypt is intentionally slow. For high-traffic validation paths,
    consider caching validated key IDs in Redis with a short TTL.
    """
    result = await db.scalars(
        select(ApiKey).where(ApiKey.is_active.is_(True))
    )
    active_keys = result.all()

    for key_row in active_keys:
        if verify_key(raw_key, key_row.key_hash):
            key_row.last_used_at = datetime.now(tz=timezone.utc)
            await db.commit()
            await db.refresh(key_row)
            return key_row

    return None
