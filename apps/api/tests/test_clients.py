from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from core.database import get_session
from main import app
from models.api_key import ApiKey
from models.client import Client
from services.api_keys import hash_api_key


class DummySession:
    pass


@pytest.fixture
def test_store() -> dict:
    tenant_id = uuid4()
    now = datetime.now(timezone.utc)
    current_client = Client(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Current Client",
        slug="current-client",
        allowed_domains=["app.example.com"],
        system_prompt="You are helpful.",
        widget_color="#111111",
        widget_greeting="Hello",
        llm_provider="openai",
        llm_model="gpt-4o",
        rate_limit_per_session=50,
        rate_limit_per_ip_hour=100,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    sibling_client = Client(
        id=uuid4(),
        tenant_id=tenant_id,
        name="Sibling Client",
        slug="sibling-client",
        allowed_domains=["shop.example.com"],
        system_prompt=None,
        widget_color=None,
        widget_greeting=None,
        llm_provider="anthropic",
        llm_model="claude-sonnet-4-20250514",
        rate_limit_per_session=75,
        rate_limit_per_ip_hour=250,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    foreign_client = Client(
        id=uuid4(),
        tenant_id=uuid4(),
        name="Foreign Client",
        slug="foreign-client",
        allowed_domains=[],
        system_prompt=None,
        widget_color=None,
        widget_greeting=None,
        llm_provider="groq",
        llm_model="llama-3.1-70b-versatile",
        rate_limit_per_session=25,
        rate_limit_per_ip_hour=50,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    api_key = ApiKey(
        id=uuid4(),
        client_id=current_client.id,
        key_hash=hash_api_key("test-key"),
        label="primary",
        is_active=True,
        last_used_at=None,
        created_at=now,
        updated_at=now,
    )
    return {
        "tenant_id": tenant_id,
        "current_client": current_client,
        "clients": {
            current_client.id: current_client,
            sibling_client.id: sibling_client,
            foreign_client.id: foreign_client,
        },
        "api_key": api_key,
    }


@pytest.fixture
def test_app(test_store: dict, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    import middleware.auth as auth_middleware
    import routers.clients as clients_router

    async def fake_get_session():
        yield DummySession()

    async def fake_resolve_client_from_api_key(_session: DummySession, api_key: str):
        if api_key == "test-key":
            return test_store["current_client"]
        return None

    async def fake_list_clients_for_tenant(_session: DummySession, tenant_id: UUID):
        return [
            client
            for client in test_store["clients"].values()
            if client.tenant_id == tenant_id
        ]

    async def fake_get_client_for_tenant(
        _session: DummySession,
        tenant_id: UUID,
        client_id: UUID,
    ):
        client = test_store["clients"].get(client_id)
        if client is None or client.tenant_id != tenant_id:
            return None
        return client

    async def fake_create_client_for_tenant(
        _session: DummySession,
        tenant_id: UUID,
        payload: dict,
    ):
        now = datetime.now(timezone.utc)
        client = Client(
            id=uuid4(),
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
            **payload,
        )
        test_store["clients"][client.id] = client
        return client

    async def fake_update_client_for_tenant(
        _session: DummySession,
        tenant_id: UUID,
        client_id: UUID,
        payload: dict,
    ):
        client = await fake_get_client_for_tenant(_session, tenant_id, client_id)
        if client is None:
            return None
        for field_name, value in payload.items():
            setattr(client, field_name, value)
        client.updated_at = datetime.now(timezone.utc)
        return client

    async def fake_delete_client_for_tenant(
        _session: DummySession,
        tenant_id: UUID,
        client_id: UUID,
    ):
        client = await fake_get_client_for_tenant(_session, tenant_id, client_id)
        if client is None:
            return False
        test_store["clients"].pop(client.id, None)
        return True

    monkeypatch.setattr(auth_middleware, "resolve_client_from_api_key", fake_resolve_client_from_api_key)
    monkeypatch.setattr(clients_router, "list_clients_for_tenant", fake_list_clients_for_tenant)
    monkeypatch.setattr(clients_router, "get_client_for_tenant", fake_get_client_for_tenant)
    monkeypatch.setattr(clients_router, "create_client_for_tenant", fake_create_client_for_tenant)
    monkeypatch.setattr(clients_router, "update_client_for_tenant", fake_update_client_for_tenant)
    monkeypatch.setattr(clients_router, "delete_client_for_tenant", fake_delete_client_for_tenant)

    app.dependency_overrides[get_session] = fake_get_session
    try:
        yield app
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncClient:
    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://test",
    ) as http_client:
        yield http_client


@pytest.mark.asyncio
async def test_list_clients_returns_current_tenant_clients(client):
    response = await client.get("/clients", headers={"X-API-Key": "test-key"})

    assert response.status_code == 200
    body = response.json()
    assert {item["slug"] for item in body} == {"current-client", "sibling-client"}
    assert all(item["tenant_id"] for item in body)


@pytest.mark.asyncio
async def test_get_client_by_id_returns_single_client(client, test_store):
    target = test_store["current_client"]
    response = await client.get(
        f"/clients/{target.id}",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == str(target.id)


@pytest.mark.asyncio
async def test_get_client_by_id_returns_404_outside_tenant(client, test_store):
    foreign_client = next(
        item for item in test_store["clients"].values() if item.tenant_id != test_store["tenant_id"]
    )
    response = await client.get(
        f"/clients/{foreign_client.id}",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_client_uses_current_tenant(client, test_store):
    response = await client.post(
        "/clients",
        headers={"X-API-Key": "test-key"},
        json={
            "name": "New Client",
            "slug": "new-client",
            "allowed_domains": ["new.example.com"],
            "llm_provider": "gemini",
            "llm_model": "gemini-2.0-flash",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["tenant_id"] == str(test_store["tenant_id"])
    assert body["slug"] == "new-client"
    assert body["allowed_domains"] == ["new.example.com"]


@pytest.mark.asyncio
async def test_update_client_changes_selected_fields(client, test_store):
    target = next(
        item for item in test_store["clients"].values() if item.slug == "sibling-client"
    )
    response = await client.patch(
        f"/clients/{target.id}",
        headers={"X-API-Key": "test-key"},
        json={"is_active": False, "rate_limit_per_session": 25},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["rate_limit_per_session"] == 25


@pytest.mark.asyncio
async def test_delete_client_removes_record(client, test_store):
    target = next(
        item for item in test_store["clients"].values() if item.slug == "sibling-client"
    )
    response = await client.delete(
        f"/clients/{target.id}",
        headers={"X-API-Key": "test-key"},
    )

    assert response.status_code == 204
    follow_up = await client.get(
        f"/clients/{target.id}",
        headers={"X-API-Key": "test-key"},
    )
    assert follow_up.status_code == 404


@pytest.mark.asyncio
async def test_missing_api_key_is_rejected(client):
    response = await client.get("/clients")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_is_rejected(client):
    response = await client.get("/clients", headers={"X-API-Key": "bad-key"})
    assert response.status_code == 401
