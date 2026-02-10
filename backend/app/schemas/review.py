from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    application_id: UUID
    framework_id: UUID
    period_start: date | None = None
    period_end: date | None = None
    due_date: date | None = None
    assigned_to: UUID | None = None


class ReviewUpdate(BaseModel):
    name: str | None = None
    due_date: date | None = None
    assigned_to: UUID | None = None
    reviewer_notes: str | None = None


class ReviewStatusUpdate(BaseModel):
    status: str


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    application_id: UUID
    framework_id: UUID
    framework_version_label: str
    period_start: date | None
    period_end: date | None
    due_date: date | None
    status: str
    analysis_checksum: str | None
    created_by: UUID | None
    assigned_to: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    reviewer_notes: str | None
    metadata: dict[str, Any] = Field(validation_alias="review_metadata")
    created_at: datetime
    updated_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_id: UUID
    filename: str
    stored_path: str
    file_hash: str
    file_size: int
    file_format: str
    template_id: UUID | None
    template_match_confidence: float | None
    document_role: str
    is_active: bool
    uploaded_by: UUID | None
    uploaded_at: datetime


class ExtractionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_id: UUID
    document_id: UUID
    record_count: int
    valid_record_count: int
    warning_count: int
    error_count: int
    confidence_score: float | None
    extraction_metadata: dict[str, Any]
    warnings: list[dict[str, Any]]
    confirmed_by: UUID | None
    confirmed_at: datetime | None
    created_at: datetime


class AnalyzeResponse(BaseModel):
    review_id: UUID
    findings_created: int
    checksum: str


class ReviewProgressEvent(BaseModel):
    event: str
    stage: str
    progress: int
    message: str
