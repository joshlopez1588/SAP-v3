from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_request_id, require_roles
from app.core.config import get_settings
from app.models import (
    Document,
    DocumentTemplate,
    Extraction,
    ExtractedRecord,
    Finding,
    Framework,
    ReferenceDataset,
    ReferenceRecord,
    Review,
    ReviewReferenceDataset,
    User,
)
from app.schemas.finding import (
    BulkDispositionRequest,
    BulkDispositionResponse,
    FindingOut,
    FindingUpdate,
)
from app.schemas.common import MessageResponse
from app.schemas.review import (
    AnalyzeResponse,
    DocumentOut,
    ExtractionOut,
    ReviewCreate,
    ReviewOut,
    ReviewStatusUpdate,
    ReviewUpdate,
)
from app.services.analysis_service import run_review_analysis
from app.services.audit_service import record_audit_event
from app.services.extraction_service import (
    apply_mapping,
    compute_extraction_checksum,
    compute_sha256,
    load_rows_from_bytes,
    parse_iso_datetime,
)

router = APIRouter(prefix="/reviews", tags=["reviews"])

ALLOWED_UPLOAD_EXTENSIONS = {".csv", ".xlsx", ".xls", ".json", ".xml", ".pdf"}

VALID_REVIEW_TRANSITIONS = {
    "created": {"documents_uploaded", "cancelled"},
    "documents_uploaded": {"extracted", "cancelled"},
    "extracted": {"analyzed", "cancelled"},
    "analyzed": {"pending_review", "cancelled"},
    "pending_review": {"approved", "cancelled"},
    "approved": {"closed"},
    "closed": set(),
    "cancelled": set(),
}


def _serialize_review(review: Review) -> ReviewOut:
    return ReviewOut.model_validate(review)


def _allowed_status_transition(current_status: str, next_status: str) -> bool:
    return next_status in VALID_REVIEW_TRANSITIONS.get(current_status, set())


async def _resolve_matching_template(
    db: AsyncSession,
    review: Review,
    filename: str,
    rows: list[dict[str, Any]],
) -> tuple[DocumentTemplate | None, float]:
    ext = Path(filename).suffix.lower().replace(".", "")

    result = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.application_id == review.application_id,
            DocumentTemplate.is_active.is_(True),
            DocumentTemplate.format == ext,
        )
    )
    templates = list(result.scalars().all())

    if not templates or not rows:
        return None, 0.0

    row_keys = set(rows[0].keys())
    best: tuple[DocumentTemplate | None, float] = (None, 0.0)
    for template in templates:
        required = set(
            (template.detection or {}).get("required_columns", [])
        )
        required = {key.strip().lower().replace(" ", "_") for key in required}
        if not required:
            continue
        overlap = len(required.intersection(row_keys)) / len(required)
        if overlap > best[1]:
            best = (template, overlap)

    return best


@router.get("", response_model=list[ReviewOut])
async def list_reviews(
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    status_filter: str | None = None,
) -> list[ReviewOut]:
    query = select(Review).where(Review.is_active.is_(True)).order_by(Review.created_at.desc())
    if status_filter:
        query = query.where(Review.status == status_filter)
    result = await db.execute(query)
    return [_serialize_review(item) for item in result.scalars().all()]


@router.post("", response_model=ReviewOut)
async def create_review(
    payload: ReviewCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewOut:
    app_result = await db.execute(
        select(Review).where(
            Review.name == payload.name,
            Review.is_active.is_(True),
        )
    )
    if app_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Review already exists")

    framework_result = await db.execute(
        select(Framework).where(
            Framework.id == payload.framework_id,
            Framework.is_active.is_(True),
        )
    )
    framework = framework_result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    review = Review(
        name=payload.name,
        application_id=payload.application_id,
        framework_id=payload.framework_id,
        framework_version_label=f"{framework.version_major}.{framework.version_minor}.{framework.version_patch}",
        period_start=payload.period_start,
        period_end=payload.period_end,
        due_date=payload.due_date,
        assigned_to=payload.assigned_to,
        status="created",
        created_by=current_user.id,
    )
    db.add(review)
    await db.flush()

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="create",
        entity_type="review",
        entity_id=review.id,
        before_state=None,
        after_state={"name": review.name, "status": review.status},
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(review)
    return _serialize_review(review)


@router.get("/{review_id}", response_model=ReviewOut)
async def get_review(
    review_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewOut:
    result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    return _serialize_review(review)


@router.put("/{review_id}", response_model=ReviewOut)
async def update_review(
    review_id: UUID,
    payload: ReviewUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewOut:
    result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    before = {
        "name": review.name,
        "due_date": review.due_date.isoformat() if review.due_date else None,
        "assigned_to": str(review.assigned_to) if review.assigned_to else None,
        "reviewer_notes": review.reviewer_notes,
    }

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(review, field, value)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="update",
        entity_type="review",
        entity_id=review.id,
        before_state=before,
        after_state=updates,
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(review)
    return _serialize_review(review)


@router.put("/{review_id}/status", response_model=ReviewOut)
async def transition_review_status(
    review_id: UUID,
    payload: ReviewStatusUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ReviewOut:
    result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    if not _allowed_status_transition(review.status, payload.status):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="STATE_TRANSITION_INVALID")

    previous_status = review.status
    review.status = payload.status

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="update",
        entity_type="review",
        entity_id=review.id,
        before_state={"status": previous_status},
        after_state={"status": payload.status},
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(review)
    return _serialize_review(review)


@router.post("/{review_id}/cancel", response_model=MessageResponse)
async def cancel_review(
    review_id: UUID,
    reason: str = Form(...),
    request: Request = None,
    current_user: User = Depends(require_roles("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    before = {"status": review.status, "reviewer_notes": review.reviewer_notes}
    review.status = "cancelled"
    review.reviewer_notes = (review.reviewer_notes or "") + f"\nCancellation reason: {reason}"

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="cancel",
        entity_type="review",
        entity_id=review.id,
        before_state=before,
        after_state={"status": review.status, "reason": reason},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Review cancelled")


@router.delete("/{review_id}", response_model=MessageResponse)
async def delete_review(
    review_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.status != "created":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Only created reviews can be deleted")

    review.is_active = False

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="delete",
        entity_type="review",
        entity_id=review.id,
        before_state={"is_active": True},
        after_state={"is_active": False},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Review deleted")


@router.post("/{review_id}/documents", response_model=DocumentOut)
async def upload_document(
    review_id: UUID,
    file: UploadFile = File(...),
    document_role: str = Form("primary"),
    request: Request = None,
    current_user: User = Depends(require_roles("admin", "analyst", "reviewer")),
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="FILE_FORMAT_UNSUPPORTED")

    content = await file.read()
    max_bytes = get_settings().max_file_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="FILE_TOO_LARGE")

    file_hash = compute_sha256(content)

    duplicate = await db.execute(
        select(Document).where(
            Document.review_id == review.id,
            Document.file_hash == file_hash,
            Document.is_active.is_(True),
        )
    )
    if duplicate.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Duplicate file upload")

    upload_dir = Path(get_settings().file_storage_path)
    upload_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = upload_dir / stored_name
    stored_path.write_bytes(content)

    parsed_rows: list[dict[str, Any]] = []
    try:
        parsed_rows = load_rows_from_bytes(file.filename, content)
    except Exception:
        parsed_rows = []

    template, confidence = await _resolve_matching_template(db, review, file.filename, parsed_rows)

    document = Document(
        review_id=review.id,
        filename=file.filename,
        stored_path=str(stored_path),
        file_hash=file_hash,
        file_size=len(content),
        file_format=ext.replace(".", ""),
        template_id=template.id if template else None,
        template_match_confidence=round(confidence, 2) if template else None,
        document_role=document_role,
        uploaded_by=current_user.id,
    )
    db.add(document)

    if review.status == "created":
        review.status = "documents_uploaded"

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="upload",
        entity_type="document",
        entity_id=document.id,
        before_state=None,
        after_state={
            "filename": document.filename,
            "file_hash": document.file_hash,
            "template_id": str(document.template_id) if document.template_id else None,
        },
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(document)
    return DocumentOut.model_validate(document)


@router.get("/{review_id}/documents", response_model=list[DocumentOut])
async def list_documents(
    review_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentOut]:
    result = await db.execute(
        select(Document)
        .where(Document.review_id == review_id, Document.is_active.is_(True))
        .order_by(Document.uploaded_at.desc())
    )
    return [DocumentOut.model_validate(item) for item in result.scalars().all()]


@router.delete("/{review_id}/documents/{document_id}", response_model=MessageResponse)
async def delete_document(
    review_id: UUID,
    document_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if review.status not in {"created", "documents_uploaded"}:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Cannot delete documents after extraction")

    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.review_id == review_id, Document.is_active.is_(True))
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    doc.is_active = False

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="delete",
        entity_type="document",
        entity_id=doc.id,
        before_state={"is_active": True},
        after_state={"is_active": False},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Document removed")


@router.post("/{review_id}/documents/{document_id}/extract", response_model=ExtractionOut)
async def extract_document(
    review_id: UUID,
    document_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExtractionOut:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    doc_result = await db.execute(
        select(Document).where(Document.id == document_id, Document.review_id == review_id, Document.is_active.is_(True))
    )
    document = doc_result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    template: DocumentTemplate | None = None
    if document.template_id:
        template_result = await db.execute(
            select(DocumentTemplate).where(DocumentTemplate.id == document.template_id, DocumentTemplate.is_active.is_(True))
        )
        template = template_result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No template matched for extraction")

    content = Path(document.stored_path).read_bytes()
    rows = load_rows_from_bytes(document.filename, content)
    extracted_rows, warnings, confidence = apply_mapping(rows, template.mapping)

    extraction = Extraction(
        review_id=review.id,
        document_id=document.id,
        template_id=template.id,
        record_count=len(extracted_rows),
        valid_record_count=len([r for r in extracted_rows if r["validation_status"] == "valid"]),
        warning_count=len(warnings),
        error_count=0,
        confidence_score=confidence,
        extraction_tool="pandas/csv",
        extraction_metadata={"template": template.name},
        warnings=warnings,
        checksum=compute_extraction_checksum(extracted_rows),
    )
    db.add(extraction)
    await db.flush()

    records_to_add: list[ExtractedRecord] = []
    for i, record in enumerate(extracted_rows):
        records_to_add.append(
            ExtractedRecord(
                extraction_id=extraction.id,
                record_index=i + 1,
                record_type="user_access",
                identifier=record.get("identifier"),
                display_name=record.get("display_name"),
                email=record.get("email"),
                status=record.get("status"),
                last_activity=parse_iso_datetime(record.get("last_activity")),
                department=record.get("department"),
                manager=record.get("manager"),
                account_type=record.get("account_type") or "human",
                roles=record.get("roles") or [],
                extended_attributes=record.get("extended_attributes") or {},
                data=record.get("data") or {},
                validation_status=record.get("validation_status") or "valid",
                validation_messages=record.get("validation_messages") or [],
            )
        )
    db.add_all(records_to_add)

    if review.status in {"created", "documents_uploaded"}:
        review.status = "extracted"

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="execute",
        entity_type="extraction",
        entity_id=extraction.id,
        before_state=None,
        after_state={
            "record_count": extraction.record_count,
            "valid_record_count": extraction.valid_record_count,
            "warning_count": extraction.warning_count,
            "confidence": float(extraction.confidence_score or 0),
        },
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(extraction)
    return ExtractionOut.model_validate(extraction)


@router.get("/{review_id}/documents/{document_id}/extraction", response_model=ExtractionOut)
async def get_extraction_result(
    review_id: UUID,
    document_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ExtractionOut:
    result = await db.execute(
        select(Extraction)
        .where(
            Extraction.review_id == review_id,
            Extraction.document_id == document_id,
            Extraction.is_active.is_(True),
        )
        .order_by(Extraction.created_at.desc())
    )
    extraction = result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")
    return ExtractionOut.model_validate(extraction)


@router.post("/{review_id}/documents/{document_id}/confirm", response_model=MessageResponse)
async def confirm_extraction(
    review_id: UUID,
    document_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    extraction_result = await db.execute(
        select(Extraction)
        .where(
            Extraction.review_id == review_id,
            Extraction.document_id == document_id,
            Extraction.is_active.is_(True),
        )
        .order_by(Extraction.created_at.desc())
    )
    extraction = extraction_result.scalar_one_or_none()
    if not extraction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extraction not found")

    extraction.confirmed_by = current_user.id
    extraction.confirmed_at = datetime.now(UTC)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="confirm",
        entity_type="extraction",
        entity_id=extraction.id,
        before_state={"confirmed_at": None},
        after_state={"confirmed_at": extraction.confirmed_at.isoformat()},
        request_id=get_request_id(request),
    )

    await db.commit()
    return MessageResponse(message="Extraction confirmed")


@router.post("/{review_id}/reference-datasets/{dataset_id}", response_model=MessageResponse)
async def attach_reference_dataset(
    review_id: UUID,
    dataset_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    if not review_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    dataset_result = await db.execute(
        select(ReferenceDataset).where(ReferenceDataset.id == dataset_id, ReferenceDataset.is_active.is_(True))
    )
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference dataset not found")

    existing_result = await db.execute(
        select(ReviewReferenceDataset).where(
            ReviewReferenceDataset.review_id == review_id,
            ReviewReferenceDataset.reference_dataset_id == dataset_id,
        )
    )
    if existing_result.scalar_one_or_none():
        return MessageResponse(message="Reference dataset already attached")

    link = ReviewReferenceDataset(
        review_id=review_id,
        reference_dataset_id=dataset_id,
        purpose="cross_reference_hr",
    )
    db.add(link)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="attach",
        entity_type="reference_dataset",
        entity_id=dataset.id,
        before_state=None,
        after_state={"review_id": str(review_id), "dataset_id": str(dataset_id)},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Reference dataset attached")


@router.post("/{review_id}/analyze", response_model=AnalyzeResponse)
async def analyze_review(
    review_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AnalyzeResponse:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    confirmed_extractions = await db.execute(
        select(Extraction).where(
            Extraction.review_id == review.id,
            Extraction.confirmed_at.is_not(None),
            Extraction.is_active.is_(True),
        )
    )
    if not confirmed_extractions.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="EXTRACTION_NOT_CONFIRMED")

    framework_result = await db.execute(select(Framework).where(Framework.id == review.framework_id, Framework.is_active.is_(True)))
    framework = framework_result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    findings_count, checksum = await run_review_analysis(db, review, framework)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="execute",
        entity_type="analysis",
        entity_id=review.id,
        before_state={"status": "extracted"},
        after_state={"status": review.status, "findings": findings_count, "checksum": checksum},
        request_id=get_request_id(request),
    )
    await db.commit()

    return AnalyzeResponse(review_id=review.id, findings_created=findings_count, checksum=checksum)


@router.get("/{review_id}/findings", response_model=list[FindingOut])
async def list_findings(
    review_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    severity: str | None = None,
) -> list[FindingOut]:
    query = select(Finding).where(Finding.review_id == review_id)
    if severity:
        query = query.where(Finding.severity == severity)
    query = query.order_by(Finding.created_at.asc())
    result = await db.execute(query)
    return [FindingOut.model_validate(item) for item in result.scalars().all()]


@router.get("/{review_id}/findings/{finding_id}", response_model=FindingOut)
async def get_finding(
    review_id: UUID,
    finding_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingOut:
    result = await db.execute(
        select(Finding).where(Finding.id == finding_id, Finding.review_id == review_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")
    return FindingOut.model_validate(finding)


@router.put("/{review_id}/findings/{finding_id}", response_model=FindingOut)
async def update_finding(
    review_id: UUID,
    finding_id: UUID,
    payload: FindingUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FindingOut:
    result = await db.execute(
        select(Finding).where(Finding.id == finding_id, Finding.review_id == review_id)
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    updates = payload.model_dump(exclude_unset=True)
    before = {
        "disposition": finding.disposition,
        "disposition_note": finding.disposition_note,
        "status": finding.status,
    }

    for field, value in updates.items():
        setattr(finding, field, value)

    if "disposition" in updates:
        finding.disposition_by = current_user.id
        finding.disposition_at = datetime.now(UTC)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="update",
        entity_type="finding",
        entity_id=finding.id,
        before_state=before,
        after_state=updates,
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(finding)
    return FindingOut.model_validate(finding)


@router.post("/{review_id}/findings/bulk-disposition", response_model=BulkDispositionResponse)
async def bulk_disposition(
    review_id: UUID,
    payload: BulkDispositionRequest,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BulkDispositionResponse:
    result = await db.execute(
        select(Finding).where(Finding.review_id == review_id, Finding.id.in_(payload.finding_ids))
    )
    findings = list(result.scalars().all())
    if len(findings) != len(payload.finding_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more findings not found")

    now = datetime.now(UTC)
    for finding in findings:
        finding.disposition = payload.disposition
        finding.disposition_note = payload.justification
        finding.disposition_by = current_user.id
        finding.disposition_at = now

        await record_audit_event(
            db,
            actor_id=current_user.id,
            actor_type="USER",
            action="update",
            entity_type="finding",
            entity_id=finding.id,
            before_state=None,
            after_state={"disposition": payload.disposition, "bulk": True},
            request_id=get_request_id(request),
            metadata={"bulk_count": len(findings)},
        )

    await db.commit()
    return BulkDispositionResponse(updated=len(findings))


@router.post("/{review_id}/approve", response_model=MessageResponse)
async def approve_review(
    review_id: UUID,
    attestation: str = Form(...),
    request: Request = None,
    current_user: User = Depends(require_roles("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    findings_result = await db.execute(select(Finding).where(Finding.review_id == review_id))
    findings = list(findings_result.scalars().all())
    missing = [f.id for f in findings if not f.disposition]
    if missing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="All findings must be dispositioned")

    review.status = "approved"
    review.approved_by = current_user.id
    review.approved_at = datetime.now(UTC)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="approve",
        entity_type="review",
        entity_id=review.id,
        before_state={"status": "pending_review"},
        after_state={"status": "approved", "attestation": attestation},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Review approved")


@router.post("/{review_id}/reject", response_model=MessageResponse)
async def reject_review(
    review_id: UUID,
    reason: str = Form(...),
    request: Request = None,
    current_user: User = Depends(require_roles("admin", "reviewer")),
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    review.status = "pending_review"
    review.reviewer_notes = (review.reviewer_notes or "") + f"\nRejection reason: {reason}"

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="reject",
        entity_type="review",
        entity_id=review.id,
        before_state={"status": "approved"},
        after_state={"status": "pending_review", "reason": reason},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Review sent back")


@router.get("/{review_id}/progress")
async def review_progress(
    review_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    review_result = await db.execute(select(Review).where(Review.id == review_id, Review.is_active.is_(True)))
    review = review_result.scalar_one_or_none()
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")

    async def event_stream():
        payload = {
            "event": "review_status",
            "review_id": str(review.id),
            "status": review.status,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        yield f"event: task_complete\ndata: {json.dumps(payload)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{review_id}/findings/{finding_id}/records")
async def finding_records(
    review_id: UUID,
    finding_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    finding_result = await db.execute(select(Finding).where(Finding.id == finding_id, Finding.review_id == review_id))
    finding = finding_result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Finding not found")

    record_ids = [UUID(rid) for rid in finding.affected_record_ids]
    if not record_ids:
        return {"items": []}

    records_result = await db.execute(select(ExtractedRecord).where(ExtractedRecord.id.in_(record_ids)))
    records = list(records_result.scalars().all())

    return {
        "items": [
            {
                "id": str(record.id),
                "identifier": record.identifier,
                "display_name": record.display_name,
                "email": record.email,
                "status": record.status,
                "last_activity": record.last_activity.isoformat() if record.last_activity else None,
                "roles": record.roles,
                "department": record.department,
                "data": record.data,
                "extended_attributes": record.extended_attributes,
            }
            for record in records
        ]
    }


reference_router = APIRouter(prefix="/reference-datasets", tags=["reference-datasets"])


@reference_router.get("", response_model=list[dict[str, Any]])
async def list_reference_datasets(
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[dict[str, Any]]:
    result = await db.execute(
        select(ReferenceDataset)
        .where(ReferenceDataset.is_active.is_(True))
        .order_by(ReferenceDataset.uploaded_at.desc())
    )
    items = []
    for dataset in result.scalars().all():
        age_days = (datetime.now(UTC).date() - dataset.uploaded_at.date()).days
        freshness = "green"
        if age_days > dataset.freshness_threshold_days:
            freshness = "red"
        elif age_days > int(dataset.freshness_threshold_days * 0.8):
            freshness = "amber"

        items.append(
            {
                "id": str(dataset.id),
                "name": dataset.name,
                "data_type": dataset.data_type,
                "source_system": dataset.source_system,
                "record_count": dataset.record_count,
                "uploaded_at": dataset.uploaded_at.isoformat(),
                "freshness_threshold_days": dataset.freshness_threshold_days,
                "freshness_status": freshness,
            }
        )
    return items


@reference_router.post("", response_model=dict[str, Any])
async def upload_reference_dataset(
    name: str = Form(...),
    data_type: str = Form(...),
    source_system: str = Form("manual"),
    freshness_threshold_days: int = Form(30),
    file: UploadFile = File(...),
    request: Request = None,
    current_user: User = Depends(require_roles("admin", "analyst")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="FILE_FORMAT_UNSUPPORTED")

    content = await file.read()
    file_hash = compute_sha256(content)

    storage_dir = Path(get_settings().file_storage_path) / "reference"
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = storage_dir / stored_name
    stored_path.write_bytes(content)

    rows = load_rows_from_bytes(file.filename, content)

    dataset = ReferenceDataset(
        name=name,
        data_type=data_type,
        source_system=source_system,
        freshness_threshold_days=freshness_threshold_days,
        file_path=str(stored_path),
        file_hash=file_hash,
        record_count=len(rows),
        uploaded_by=current_user.id,
    )
    db.add(dataset)
    await db.flush()

    records: list[ReferenceRecord] = []
    for idx, row in enumerate(rows):
        records.append(
            ReferenceRecord(
                dataset_id=dataset.id,
                record_index=idx + 1,
                identifier=row.get("employee_id") or row.get("identifier") or row.get("userid"),
                display_name=row.get("name") or row.get("display_name") or row.get("username"),
                email=(row.get("email") or "").lower() if row.get("email") else None,
                employment_status=(row.get("status") or row.get("employment_status") or "").lower() or None,
                department=row.get("department"),
            )
        )
    db.add_all(records)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="upload",
        entity_type="reference_dataset",
        entity_id=dataset.id,
        before_state=None,
        after_state={"name": name, "record_count": len(rows)},
        request_id=get_request_id(request),
    )
    await db.commit()

    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "record_count": dataset.record_count,
        "file_hash": dataset.file_hash,
    }


@reference_router.get("/{dataset_id}")
async def get_reference_dataset(
    dataset_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    dataset_result = await db.execute(
        select(ReferenceDataset).where(ReferenceDataset.id == dataset_id, ReferenceDataset.is_active.is_(True))
    )
    dataset = dataset_result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    records_result = await db.execute(
        select(ReferenceRecord)
        .where(ReferenceRecord.dataset_id == dataset.id)
        .order_by(ReferenceRecord.record_index.asc())
        .limit(5)
    )
    sample = list(records_result.scalars().all())

    return {
        "id": str(dataset.id),
        "name": dataset.name,
        "data_type": dataset.data_type,
        "source_system": dataset.source_system,
        "record_count": dataset.record_count,
        "uploaded_at": dataset.uploaded_at.isoformat(),
        "file_hash": dataset.file_hash,
        "sample_records": [
            {
                "identifier": rec.identifier,
                "display_name": rec.display_name,
                "email": rec.email,
                "employment_status": rec.employment_status,
                "department": rec.department,
            }
            for rec in sample
        ],
    }


@reference_router.get("/{dataset_id}/records")
async def get_reference_dataset_records(
    dataset_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 200,
) -> dict[str, Any]:
    result = await db.execute(
        select(ReferenceRecord)
        .where(ReferenceRecord.dataset_id == dataset_id)
        .order_by(ReferenceRecord.record_index.asc())
        .limit(min(limit, 200))
    )
    rows = list(result.scalars().all())
    return {
        "items": [
            {
                "id": str(row.id),
                "record_index": row.record_index,
                "identifier": row.identifier,
                "display_name": row.display_name,
                "email": row.email,
                "employment_status": row.employment_status,
                "department": row.department,
            }
            for row in rows
        ]
    }


@reference_router.delete("/{dataset_id}", response_model=MessageResponse)
async def deactivate_reference_dataset(
    dataset_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    result = await db.execute(
        select(ReferenceDataset).where(ReferenceDataset.id == dataset_id, ReferenceDataset.is_active.is_(True))
    )
    dataset = result.scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    dataset.is_active = False

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="delete",
        entity_type="reference_dataset",
        entity_id=dataset.id,
        before_state={"is_active": True},
        after_state={"is_active": False},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Reference dataset deactivated")
