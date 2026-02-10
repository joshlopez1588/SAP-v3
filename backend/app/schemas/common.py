from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class APIError(BaseModel):
    code: str
    message: str
    details: list[dict[str, str]] | None = None
    request_id: str | None = None


class APIErrorEnvelope(BaseModel):
    error: APIError


class PaginatedResponse(BaseModel):
    items: list[Any]
    next_cursor: str | None = None
    has_more: bool = False
    total: int | None = None


class HealthCheckResponse(BaseModel):
    status: str
    version: str
    uptime_seconds: int
    checks: dict[str, dict[str, Any]]


class MessageResponse(BaseModel):
    message: str


class TimestampedModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    created_at: datetime
    updated_at: datetime | None = None
