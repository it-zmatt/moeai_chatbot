import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_session
from models.tenant import Tenant
from schemas.tenant import TenantCreate, TenantResponse, TenantUpdate

router = APIRouter(tags=["tenants"])


# ---------------------------------------------------------------------------
# GET /tenants — list all
# ---------------------------------------------------------------------------


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    db: AsyncSession = Depends(get_session),
) -> list[Tenant]:
    result = await db.execute(select(Tenant).order_by(Tenant.created_at.desc()))
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# GET /tenants/{id} — fetch by UUID
# ---------------------------------------------------------------------------


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


# ---------------------------------------------------------------------------
# POST /tenants — create
# ---------------------------------------------------------------------------


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_session),
) -> Tenant:
    tenant = Tenant(**payload.model_dump(mode="json"))
    db.add(tenant)
    try:
        await db.commit()
        await db.refresh(tenant)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this slug already exists",
        )
    return tenant


# ---------------------------------------------------------------------------
# PATCH /tenants/{id} — partial update
# ---------------------------------------------------------------------------


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    db: AsyncSession = Depends(get_session),
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    updates = payload.model_dump(exclude_unset=True, mode="json")
    for field, value in updates.items():
        setattr(tenant, field, value)

    try:
        await db.commit()
        await db.refresh(tenant)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A tenant with this slug already exists",
        )
    return tenant


# ---------------------------------------------------------------------------
# DELETE /tenants/{id} — hard delete
# ---------------------------------------------------------------------------


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    await db.delete(tenant)
    await db.commit()
