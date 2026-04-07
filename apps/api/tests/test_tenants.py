"""Tests for GET /tenants, GET /tenants/{id}, POST /tenants, PATCH /tenants/{id}, DELETE /tenants/{id}."""

import uuid

import pytest


def unique_tenant_payload() -> dict:
    suffix = uuid.uuid4().hex[:12]
    return {
        "name": "Acme Corp",
        "slug": f"acme-{suffix}",
        "contact_email": f"admin-{suffix}@acme.com",
        "plan": "starter",
    }


async def _create_tenant(client, payload: dict | None = None) -> dict:
    data = payload or unique_tenant_payload()
    r = await client.post("/tenants", json=data)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.asyncio
async def test_list_tenants_returns_json_list(client):
    r = await client.get("/tenants")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_list_tenants_returns_created(client):
    payload = unique_tenant_payload()
    created = await _create_tenant(client, payload)
    r = await client.get("/tenants")
    assert r.status_code == 200
    tenants = r.json()
    ids = {t["id"] for t in tenants}
    assert created["id"] in ids
    match = next(t for t in tenants if t["id"] == created["id"])
    assert match["slug"] == payload["slug"]


@pytest.mark.asyncio
async def test_get_tenant_by_id(client):
    created = await _create_tenant(client)
    r = await client.get(f"/tenants/{created['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == created["id"]
    assert r.json()["name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_get_tenant_not_found(client):
    r = await client.get("/tenants/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
    assert r.json()["detail"] == "Tenant not found"


@pytest.mark.asyncio
async def test_create_tenant_returns_201(client):
    payload = unique_tenant_payload()
    r = await client.post("/tenants", json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["slug"] == payload["slug"]
    assert body["plan"] == "starter"
    assert body["is_active"] is True
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug_returns_409(client):
    payload = unique_tenant_payload()
    await _create_tenant(client, payload)
    r = await client.post(
        "/tenants",
        json={**payload, "name": "Another Corp"},
    )
    assert r.status_code == 409
    assert "slug" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_patch_tenant(client):
    created = await _create_tenant(client)
    r = await client.patch(
        f"/tenants/{created['id']}",
        json={"plan": "pro", "is_active": False},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["plan"] == "pro"
    assert body["is_active"] is False
    assert body["name"] == "Acme Corp"


@pytest.mark.asyncio
async def test_patch_tenant_not_found(client):
    r = await client.patch(
        "/tenants/00000000-0000-0000-0000-000000000000",
        json={"plan": "pro"},
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_delete_tenant(client):
    created = await _create_tenant(client)
    r = await client.delete(f"/tenants/{created['id']}")
    assert r.status_code == 204

    r2 = await client.get(f"/tenants/{created['id']}")
    assert r2.status_code == 404


@pytest.mark.asyncio
async def test_delete_tenant_not_found(client):
    r = await client.delete("/tenants/00000000-0000-0000-0000-000000000000")
    assert r.status_code == 404
