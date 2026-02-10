from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_id: UUID
    check_id: str
    check_name: str
    severity: str
    explainability: str
    ai_description: str | None
    ai_remediation: str | None
    ai_generated: bool
    ai_confidence: float | None
    disposition: str | None
    disposition_by: UUID | None
    disposition_at: datetime | None
    disposition_note: str | None
    status: str
    record_count: int
    affected_record_ids: list[str]
    output_fields: list[str]
    notes: str | None
    created_at: datetime
    updated_at: datetime


class FindingUpdate(BaseModel):
    disposition: str | None = Field(default=None)
    disposition_note: str | None = Field(default=None, max_length=10000)
    status: str | None = None
    notes: str | None = Field(default=None, max_length=10000)


class BulkDispositionRequest(BaseModel):
    finding_ids: list[UUID] = Field(min_length=1, max_length=200)
    disposition: str
    justification: str = Field(min_length=1, max_length=10000)


class BulkDispositionResponse(BaseModel):
    updated: int
