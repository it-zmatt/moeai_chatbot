import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class TenantPlan(str, Enum):
    free = "free"
    starter = "starter"
    pro = "pro"
    enterprise = "enterprise"


class TenantCreate(BaseModel):
    name: str
    slug: str
    contact_email: str
    plan: TenantPlan = TenantPlan.free
    is_active: bool = True


class TenantUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    contact_email: str | None = None
    plan: TenantPlan | None = None
    is_active: bool | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    contact_email: str
    plan: TenantPlan
    is_active: bool
    created_at: datetime
    updated_at: datetime
