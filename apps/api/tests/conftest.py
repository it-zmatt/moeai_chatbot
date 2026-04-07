from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import os  # noqa: E402
import uuid  # noqa: E402

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from core.database import AsyncSessionLocal, engine  # noqa: E402
from main import app  # noqa: E402
from models.tenant import Tenant  # noqa: E402


@pytest.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def http_client(client: AsyncClient) -> AsyncClient:
    """Alias used by ``test_api_keys.py``."""
    yield client


@pytest.fixture
async def tenant_id() -> uuid.UUID:
    tid = uuid.uuid4()
    async with AsyncSessionLocal() as session:
        session.add(
            Tenant(
                id=tid,
                name="pytest tenant",
                slug=f"pytest-{tid.hex[:20]}",
                contact_email=f"{tid.hex[:12]}@pytest.example",
            )
        )
        await session.commit()
    yield tid
    async with AsyncSessionLocal() as session:
        await session.execute(delete(Tenant).where(Tenant.id == tid))
        await session.commit()


@pytest.fixture(autouse=True)
async def dispose_sqlalchemy_engine() -> None:
    yield
    await engine.dispose()


def pytest_configure(config: pytest.Config) -> None:
    if not os.environ.get("DATABASE_URL"):
        config.addinivalue_line(
            "markers",
            "integration: requires DATABASE_URL (set in environment or apps/api/.env)",
        )
