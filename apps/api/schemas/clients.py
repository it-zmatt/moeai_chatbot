import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

LLM_PROVIDERS = frozenset({"openai", "anthropic", "groq", "mistral", "gemini"})


class ClientCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=10_000)
    slug: str = Field(min_length=1, max_length=500, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    allowed_domains: list[str] = Field(default_factory=list)
    system_prompt: str | None = None
    widget_color: str | None = None
    widget_greeting: str | None = None
    llm_provider: str = "openai"
    llm_model: str = "gpt-4o"
    rate_limit_per_session: int = Field(default=50, ge=1)
    rate_limit_per_ip_hour: int = Field(default=100, ge=1)
    is_active: bool = True

    @field_validator("llm_provider")
    @classmethod
    def llm_provider_allowed(cls, v: str) -> str:
        if v not in LLM_PROVIDERS:
            msg = f"llm_provider must be one of: {', '.join(sorted(LLM_PROVIDERS))}"
            raise ValueError(msg)
        return v


class ClientUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=10_000)
    slug: str | None = Field(
        default=None, min_length=1, max_length=500, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    allowed_domains: list[str] | None = None
    system_prompt: str | None = None
    widget_color: str | None = None
    widget_greeting: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    rate_limit_per_session: int | None = Field(default=None, ge=1)
    rate_limit_per_ip_hour: int | None = Field(default=None, ge=1)
    is_active: bool | None = None

    @field_validator("llm_provider")
    @classmethod
    def llm_provider_allowed(cls, v: str | None) -> str | None:
        if v is not None and v not in LLM_PROVIDERS:
            msg = f"llm_provider must be one of: {', '.join(sorted(LLM_PROVIDERS))}"
            raise ValueError(msg)
        return v


class ClientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    slug: str
    allowed_domains: list[str]
    system_prompt: str | None
    widget_color: str | None
    widget_greeting: str | None
    llm_provider: str
    llm_model: str
    rate_limit_per_session: int
    rate_limit_per_ip_hour: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
