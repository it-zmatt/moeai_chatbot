from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

ClientProvider = Literal["openai", "anthropic", "groq", "mistral", "gemini"]


class ClientBase(BaseModel):
    name: str
    slug: str
    allowed_domains: list[str] = Field(default_factory=list)
    system_prompt: str | None = None
    widget_color: str | None = None
    widget_greeting: str | None = None
    llm_provider: ClientProvider = "openai"
    llm_model: str = "gpt-4o"
    rate_limit_per_session: int = 50
    rate_limit_per_ip_hour: int = 100
    is_active: bool = True


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None
    allowed_domains: list[str] | None = None
    system_prompt: str | None = None
    widget_color: str | None = None
    widget_greeting: str | None = None
    llm_provider: ClientProvider | None = None
    llm_model: str | None = None
    rate_limit_per_session: int | None = None
    rate_limit_per_ip_hour: int | None = None
    is_active: bool | None = None


class ClientResponse(ClientBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
