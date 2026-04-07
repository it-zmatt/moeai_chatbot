from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.database import engine
from middleware.auth import api_key_auth_middleware
from routers import clients, health, tenants
from routers.api_keys import keys_router, validate_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="MoeAI API", lifespan=lifespan)
app.middleware("http")(api_key_auth_middleware)
app.include_router(health.router)
app.include_router(tenants.router, prefix="/tenants")
app.include_router(clients.router)
app.include_router(keys_router, prefix="/clients/{client_id}")
app.include_router(validate_router)
