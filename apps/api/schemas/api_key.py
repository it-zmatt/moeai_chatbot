import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=255)


class ApiKeyUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=255)


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    client_id: uuid.UUID
    label: str | None
    is_active: bool
    last_used_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned only on POST /api-keys — raw_key is shown exactly once."""

    raw_key: str


class ApiKeyValidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    raw_key: str


class ApiKeyValidateResponse(BaseModel):
    valid: bool
    client_id: uuid.UUID | None = None
    key_id: uuid.UUID | None = None
