from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FrameworkBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    review_type: str = Field(min_length=1, max_length=50)
    settings: dict[str, Any] = Field(default_factory=dict)
    checks: list[dict[str, Any]] = Field(default_factory=list, max_length=100)
    regulatory_mappings: list[dict[str, Any]] = Field(default_factory=list, max_length=20)
    effective_date: date | None = None


class FrameworkCreate(FrameworkBase):
    pass


class FrameworkUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    settings: dict[str, Any] | None = None
    checks: list[dict[str, Any]] | None = Field(default=None, max_length=100)
    regulatory_mappings: list[dict[str, Any]] | None = Field(default=None, max_length=20)
    effective_date: date | None = None


class FrameworkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    review_type: str
    version_major: int
    version_minor: int
    version_patch: int
    settings: dict[str, Any]
    checks: list[dict[str, Any]]
    regulatory_mappings: list[dict[str, Any]]
    status: str
    is_active: bool
    is_immutable: bool
    effective_date: date | None
    created_at: datetime
    updated_at: datetime


class FrameworkPublishResponse(BaseModel):
    id: UUID
    version_label: str
    status: str
