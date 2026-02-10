from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    timestamp: datetime
    actor_id: UUID | None
    actor_type: str
    request_id: str | None
    action: str
    entity_type: str
    entity_id: UUID | None
    content_hash: str
    previous_hash: str | None
    metadata: dict = Field(validation_alias="audit_metadata")


class AuditVerificationResponse(BaseModel):
    valid: bool
    checked_entries: int
    first_invalid_id: int | None = None
    message: str
