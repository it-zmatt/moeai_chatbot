"""
Integration tests for the API Keys CRUD (Step 6).

Requirements:
  DATABASE_URL env var pointing to a running Postgres instance with
  migrations applied (supabase db reset or equivalent).

Run:
  cd apps/api
  pytest tests/test_api_keys.py -v
"""

import os
import uuid

import pytest
from sqlalchemy import delete

from core.database import AsyncSessionLocal
from models.client import Client
from models.tenant import Tenant

pytestmark = pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL not set — integration tests skipped",
)

BASE = "/clients"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def client_id(tenant_id) -> uuid.UUID:
    """Create a fresh Client row owned by the shared tenant fixture."""
    cid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Client(
                id=cid,
                tenant_id=tenant_id,
                name="Test Client",
                slug=f"test-{cid.hex[:16]}",
                llm_provider="openai",
                llm_model="gpt-4o",
            )
        )
        await session.commit()
    yield cid
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Client).where(Client.id == cid))
        await session.commit()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _create_key(http_client, client_id, label=None):
    body = {"label": label} if label is not None else {}
    r = await http_client.post(f"{BASE}/{client_id}/api-keys", json=body)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# Test 1-3: GET list
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_keys_empty(http_client, client_id):
    """Test 1 — valid client, no keys yet → empty list."""
    r = await http_client.get(f"{BASE}/{client_id}/api-keys")
    assert r.status_code == 200
    assert r.json() == []


@pytest.mark.asyncio
async def test_list_keys_active_only(http_client, client_id):
    """Test 2 — ?active_only=true filters revoked keys."""
    created = await _create_key(http_client, client_id, label="to-revoke")
    key_id = created["id"]

    # Revoke it
    r = await http_client.delete(f"{BASE}/{client_id}/api-keys/{key_id}")
    assert r.status_code == 200

    # Without filter: still appears
    r = await http_client.get(f"{BASE}/{client_id}/api-keys")
    assert any(k["id"] == key_id for k in r.json())

    # With filter: gone
    r = await http_client.get(f"{BASE}/{client_id}/api-keys?active_only=true")
    assert r.status_code == 200
    assert not any(k["id"] == key_id for k in r.json())


@pytest.mark.asyncio
async def test_list_keys_unknown_client(http_client):
    """Test 3 — unknown client_id → 404."""
    r = await http_client.get(f"{BASE}/{uuid.uuid4()}/api-keys")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test 4-6: GET single
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_key_by_id(http_client, client_id):
    """Test 4 — fetch a specific key by ID."""
    created = await _create_key(http_client, client_id, label="fetch-me")
    key_id = created["id"]

    r = await http_client.get(f"{BASE}/{client_id}/api-keys/{key_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == key_id
    assert data["label"] == "fetch-me"
    assert "key_hash" not in data


@pytest.mark.asyncio
async def test_get_key_wrong_client(http_client, tenant_id, client_id):
    """Test 5 — key belongs to a different client → 404."""
    other_cid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Client(
                id=other_cid,
                tenant_id=tenant_id,
                name="Other",
                slug=f"other-{other_cid.hex[:12]}",
                llm_provider="openai",
                llm_model="gpt-4o",
            )
        )
        await session.commit()

    try:
        created = await _create_key(http_client, client_id, label="mine")
        key_id = created["id"]

        r = await http_client.get(f"{BASE}/{other_cid}/api-keys/{key_id}")
        assert r.status_code == 404
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Client).where(Client.id == other_cid))
            await session.commit()


@pytest.mark.asyncio
async def test_get_key_unknown_id(http_client, client_id):
    """Test 6 — unknown key_id → 404."""
    r = await http_client.get(f"{BASE}/{client_id}/api-keys/{uuid.uuid4()}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test 7-10: POST generate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_key_with_label(http_client, client_id):
    """Test 7 — create with label → 201, raw_key present."""
    data = await _create_key(http_client, client_id, label="prod-key")
    assert data["label"] == "prod-key"
    assert data["is_active"] is True
    assert data["last_used_at"] is None
    assert "raw_key" in data
    assert data["raw_key"].startswith("moe_")
    assert "key_hash" not in data


@pytest.mark.asyncio
async def test_create_key_no_label(http_client, client_id):
    """Test 8 — create without label → label is null."""
    data = await _create_key(http_client, client_id)
    assert data["label"] is None
    assert "raw_key" in data


@pytest.mark.asyncio
async def test_create_key_unknown_client(http_client):
    """Test 9 — unknown client_id → 404."""
    r = await http_client.post(f"{BASE}/{uuid.uuid4()}/api-keys", json={"label": "x"})
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_key_hash_differs_from_raw(http_client, client_id):
    """Test 10 — raw_key in response must not equal key_hash in DB."""
    from models.api_key import ApiKey

    data = await _create_key(http_client, client_id, label="security-check")
    raw = data["raw_key"]
    key_id = uuid.UUID(data["id"])

    async with AsyncSessionLocal() as session:
        row = await session.get(ApiKey, key_id)
        assert row is not None
        assert row.key_hash != raw
        assert row.key_hash.startswith("$2b$")  # bcrypt sentinel


# ---------------------------------------------------------------------------
# Test 11-12: PATCH
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patch_label(http_client, client_id):
    """Test 11 — update label."""
    created = await _create_key(http_client, client_id, label="old-label")
    key_id = created["id"]

    r = await http_client.patch(
        f"{BASE}/{client_id}/api-keys/{key_id}",
        json={"label": "new-label"},
    )
    assert r.status_code == 200
    assert r.json()["label"] == "new-label"
    assert "raw_key" not in r.json()


@pytest.mark.asyncio
async def test_patch_wrong_client(http_client, tenant_id, client_id):
    """Test 12 — patch key belonging to different client → 404."""
    other_cid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Client(
                id=other_cid,
                tenant_id=tenant_id,
                name="Other2",
                slug=f"other2-{other_cid.hex[:10]}",
                llm_provider="openai",
                llm_model="gpt-4o",
            )
        )
        await session.commit()

    try:
        created = await _create_key(http_client, client_id, label="mine2")
        key_id = created["id"]
        r = await http_client.patch(
            f"{BASE}/{other_cid}/api-keys/{key_id}",
            json={"label": "stolen"},
        )
        assert r.status_code == 404
    finally:
        async with AsyncSessionLocal() as session:
            await session.execute(delete(Client).where(Client.id == other_cid))
            await session.commit()


# ---------------------------------------------------------------------------
# Test 13-15: DELETE (revoke)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revoke_active_key(http_client, client_id):
    """Test 13 — revoke an active key → is_active=false."""
    created = await _create_key(http_client, client_id, label="to-revoke-2")
    key_id = created["id"]

    r = await http_client.delete(f"{BASE}/{client_id}/api-keys/{key_id}")
    assert r.status_code == 200
    assert r.json()["is_active"] is False


@pytest.mark.asyncio
async def test_revoke_idempotent(http_client, client_id):
    """Test 14 — revoking an already-revoked key is idempotent → 200."""
    created = await _create_key(http_client, client_id, label="idempotent")
    key_id = created["id"]

    r1 = await http_client.delete(f"{BASE}/{client_id}/api-keys/{key_id}")
    assert r1.status_code == 200
    r2 = await http_client.delete(f"{BASE}/{client_id}/api-keys/{key_id}")
    assert r2.status_code == 200
    assert r2.json()["is_active"] is False


@pytest.mark.asyncio
async def test_revoke_unknown_key(http_client, client_id):
    """Test 15 — unknown key_id → 404."""
    r = await http_client.delete(f"{BASE}/{client_id}/api-keys/{uuid.uuid4()}")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Test 16-19: POST /api-keys/validate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validate_valid_key(http_client, client_id):
    """Test 16 — valid raw_key → 200, valid=true, client_id returned."""
    created = await _create_key(http_client, client_id, label="validate-me")
    raw_key = created["raw_key"]

    r = await http_client.post("/api-keys/validate", json={"raw_key": raw_key})
    assert r.status_code == 200
    data = r.json()
    assert data["valid"] is True
    assert data["client_id"] == str(client_id)
    assert data["key_id"] == created["id"]


@pytest.mark.asyncio
async def test_validate_wrong_key(http_client, client_id):
    """Test 17 — wrong raw_key value → 401."""
    await _create_key(http_client, client_id, label="wrong-test")
    r = await http_client.post("/api-keys/validate", json={"raw_key": "moe_notarealkey"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_validate_revoked_key(http_client, client_id):
    """Test 18 — revoked key cannot be validated → 401."""
    created = await _create_key(http_client, client_id, label="revoke-then-validate")
    key_id = created["id"]
    raw_key = created["raw_key"]

    await http_client.delete(f"{BASE}/{client_id}/api-keys/{key_id}")

    r = await http_client.post("/api-keys/validate", json={"raw_key": raw_key})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_validate_updates_last_used_at(http_client, client_id):
    """Test 19 — successful validation updates last_used_at in DB."""
    from models.api_key import ApiKey

    created = await _create_key(http_client, client_id, label="track-last-used")
    raw_key = created["raw_key"]
    key_id = uuid.UUID(created["id"])

    # Confirm last_used_at is null before validation
    async with AsyncSessionLocal() as session:
        row = await session.get(ApiKey, key_id)
        assert row.last_used_at is None

    r = await http_client.post("/api-keys/validate", json={"raw_key": raw_key})
    assert r.status_code == 200

    async with AsyncSessionLocal() as session:
        row = await session.get(ApiKey, key_id)
        assert row.last_used_at is not None
