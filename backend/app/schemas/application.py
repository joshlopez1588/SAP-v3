from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ApplicationBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    review_type: str = Field(min_length=1, max_length=50)
    owner: str | None = Field(default=None, max_length=255)
    owner_email: EmailStr | None = None
    criticality: str = "medium"
    data_classification: str = "internal"
    context: str | None = Field(default=None, max_length=5000)
    role_definitions: list[dict[str, Any]] = Field(default_factory=list)
    regulatory_scope: list[str] = Field(default_factory=list)
    review_frequency: str = "quarterly"
    next_review_date: date | None = None
    reminder_days: list[int] = Field(default_factory=lambda: [30, 14, 7])
    escalation_after_days: int = 14


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    owner: str | None = Field(default=None, max_length=255)
    owner_email: EmailStr | None = None
    criticality: str | None = None
    data_classification: str | None = None
    context: str | None = Field(default=None, max_length=5000)
    role_definitions: list[dict[str, Any]] | None = None
    regulatory_scope: list[str] | None = None
    review_frequency: str | None = None
    next_review_date: date | None = None
    reminder_days: list[int] | None = None
    escalation_after_days: int | None = None


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    review_type: str
    owner: str | None
    owner_email: str | None
    criticality: str
    data_classification: str
    context: str | None
    role_definitions: list[dict[str, Any]]
    regulatory_scope: list[str]
    review_frequency: str
    next_review_date: date | None
    reminder_days: list[int]
    escalation_after_days: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DocumentTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    format: str
    detection: dict[str, Any] = Field(default_factory=dict)
    mapping: dict[str, Any] = Field(default_factory=dict)
    validation: list[dict[str, Any]] = Field(default_factory=list)
    confidence_threshold: float = 0.95


class DocumentTemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_id: UUID
    name: str
    description: str | None
    format: str
    detection: dict[str, Any]
    mapping: dict[str, Any]
    validation: list[dict[str, Any]]
    confidence_threshold: float
    version: int
    created_at: datetime
    updated_at: datetime
