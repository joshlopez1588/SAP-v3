from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class SoftDeleteMixin:
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="analyst")
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Invite(Base):
    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="analyst")
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    used_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Framework(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "frameworks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_type: Mapped[str] = mapped_column(String(50), index=True)
    version_major: Mapped[int] = mapped_column(Integer, default=1)
    version_minor: Mapped[int] = mapped_column(Integer, default=0)
    version_patch: Mapped[int] = mapped_column(Integer, default=0)
    effective_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    settings: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    regulatory_mappings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(30), default="draft")
    is_immutable: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_framework_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("frameworks.id", ondelete="SET NULL"), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Application(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_type: Mapped[str] = mapped_column(String(50), index=True)
    owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    criticality: Mapped[str] = mapped_column(String(20), default="medium")
    data_classification: Mapped[str] = mapped_column(String(20), default="internal")
    context: Mapped[str | None] = mapped_column(Text, nullable=True)
    role_definitions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    regulatory_scope: Mapped[list[str]] = mapped_column(JSON, default=list)
    review_frequency: Mapped[str] = mapped_column(String(20), default="quarterly")
    next_review_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reminder_days: Mapped[list[int]] = mapped_column(JSON, default=lambda: [30, 14, 7])
    escalation_after_days: Mapped[int] = mapped_column(Integer, default=14)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class DocumentTemplate(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "document_templates"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("applications.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    format: Mapped[str] = mapped_column(String(50))
    detection: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    mapping: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    confidence_threshold: Mapped[Decimal] = mapped_column(Numeric(5, 4), default=Decimal("0.9500"))
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class Review(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    application_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("applications.id", ondelete="RESTRICT"), index=True)
    framework_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("frameworks.id", ondelete="RESTRICT"), index=True)
    framework_version_label: Mapped[str] = mapped_column(String(20))
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="created", index=True)
    previous_review_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="SET NULL"), nullable=True)
    analysis_checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    ai_summary_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_summary_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reviewer_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)


class ReviewComment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "review_comments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("findings.id", ondelete="CASCADE"), nullable=True)
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("review_comments.id", ondelete="CASCADE"), nullable=True)
    author_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="RESTRICT"))
    body: Mapped[str] = mapped_column(Text)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64), index=True)
    file_size: Mapped[int] = mapped_column(Integer)
    file_format: Mapped[str] = mapped_column(String(50))
    template_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True)
    template_match_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    document_role: Mapped[str] = mapped_column(String(50), default="primary")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True)
    record_count: Mapped[int] = mapped_column(Integer)
    valid_record_count: Mapped[int] = mapped_column(Integer)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    extraction_tool: Mapped[str | None] = mapped_column(String(100), nullable=True)
    extraction_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    warnings: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    checksum: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ExtractedRecord(Base):
    __tablename__ = "extracted_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    extraction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("extractions.id", ondelete="CASCADE"), index=True)
    record_index: Mapped[int] = mapped_column(Integer)
    record_type: Mapped[str] = mapped_column(String(50), default="user_access")

    identifier: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    manager: Mapped[str | None] = mapped_column(String(255), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(50), nullable=True, default="human")
    roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    extended_attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_status: Mapped[str] = mapped_column(String(20), default="valid")
    validation_messages: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReferenceDataset(Base):
    __tablename__ = "reference_datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_type: Mapped[str] = mapped_column(String(50), index=True)
    source_system: Mapped[str | None] = mapped_column(String(255), nullable=True)
    freshness_threshold_days: Mapped[int] = mapped_column(Integer, default=30)
    file_path: Mapped[str] = mapped_column(String(500))
    file_hash: Mapped[str] = mapped_column(String(64))
    record_count: Mapped[int] = mapped_column(Integer)
    template_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True)
    uploaded_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class ReferenceRecord(Base):
    __tablename__ = "reference_records"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reference_datasets.id", ondelete="CASCADE"), index=True)
    record_index: Mapped[int] = mapped_column(Integer)
    identifier: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    employment_status: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    department: Mapped[str | None] = mapped_column(String(255), nullable=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extended_attributes: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReviewReferenceDataset(Base):
    __tablename__ = "review_reference_datasets"
    __table_args__ = (
        UniqueConstraint("review_id", "reference_dataset_id", name="uq_review_reference_dataset"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    reference_dataset_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reference_datasets.id", ondelete="RESTRICT"), index=True)
    purpose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="CASCADE"), index=True)
    check_id: Mapped[str] = mapped_column(String(100), index=True)
    check_name: Mapped[str] = mapped_column(String(255))
    severity: Mapped[str] = mapped_column(String(50), index=True)
    explainability: Mapped[str] = mapped_column(Text)

    ai_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_remediation: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    disposition: Mapped[str | None] = mapped_column(String(50), nullable=True)
    disposition_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    disposition_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disposition_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(String(50), default="open")
    record_count: Mapped[int] = mapped_column(Integer)
    affected_record_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    output_fields: Mapped[list[str]] = mapped_column(JSON, default=list)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), default="USER")
    session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(50), index=True)
    entity_type: Mapped[str] = mapped_column(String(50), index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    before_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    audit_metadata: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_input_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_output_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_confidence: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    ai_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)


class AIInvocation(Base):
    __tablename__ = "ai_invocations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="SET NULL"), nullable=True, index=True)
    finding_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("findings.id", ondelete="SET NULL"), nullable=True)
    function_type: Mapped[str] = mapped_column(String(50))
    model_name: Mapped[str] = mapped_column(String(100))
    model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    input_hash: Mapped[str] = mapped_column(String(64))
    output_hash: Mapped[str] = mapped_column(String(64))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(3, 2), nullable=True)
    temperature: Mapped[Decimal | None] = mapped_column(Numeric(2, 1), nullable=True)
    token_count_input: Mapped[int | None] = mapped_column(Integer, nullable=True)
    token_count_output: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIUsageLog(Base):
    __tablename__ = "ai_usage_log"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("reviews.id", ondelete="SET NULL"), nullable=True, index=True)
    invocation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("ai_invocations.id", ondelete="SET NULL"), nullable=True)
    model_name: Mapped[str] = mapped_column(String(100))
    function_type: Mapped[str] = mapped_column(String(50))
    tokens_input: Mapped[int] = mapped_column(Integer, default=0)
    tokens_output: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    success: Mapped[bool] = mapped_column(Boolean, default=True)
    error_code: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
