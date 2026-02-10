from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_request_id, require_roles
from app.models import Application, DocumentTemplate, User
from app.schemas.application import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    DocumentTemplateCreate,
    DocumentTemplateOut,
)
from app.schemas.common import MessageResponse
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationOut])
async def list_applications(
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApplicationOut]:
    result = await db.execute(
        select(Application).where(Application.is_active.is_(True)).order_by(Application.name.asc())
    )
    return [ApplicationOut.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=ApplicationOut)
async def create_application(
    payload: ApplicationCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationOut:
    exists = await db.execute(
        select(Application).where(Application.name == payload.name, Application.is_active.is_(True))
    )
    if exists.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Application already exists")

    app = Application(**payload.model_dump(), created_by=current_user.id)
    db.add(app)
    await db.flush()

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="create",
        entity_type="application",
        entity_id=app.id,
        before_state=None,
        after_state={"name": app.name, "review_type": app.review_type},
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(app)
    return ApplicationOut.model_validate(app)


@router.get("/{application_id}", response_model=ApplicationOut)
async def get_application(
    application_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationOut:
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.is_active.is_(True))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    return ApplicationOut.model_validate(app)


@router.put("/{application_id}", response_model=ApplicationOut)
async def update_application(
    application_id: UUID,
    payload: ApplicationUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApplicationOut:
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.is_active.is_(True))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    before = payload.model_dump(exclude_unset=False)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(app, field, value)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="update",
        entity_type="application",
        entity_id=app.id,
        before_state=before,
        after_state=updates,
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(app)
    return ApplicationOut.model_validate(app)


@router.delete("/{application_id}", response_model=MessageResponse)
async def delete_application(
    application_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    result = await db.execute(
        select(Application).where(Application.id == application_id, Application.is_active.is_(True))
    )
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    app.is_active = False

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="delete",
        entity_type="application",
        entity_id=app.id,
        before_state={"is_active": True},
        after_state={"is_active": False},
        request_id=get_request_id(request),
    )

    await db.commit()
    return MessageResponse(message="Application archived")


@router.post("/{application_id}/templates", response_model=DocumentTemplateOut)
async def create_template(
    application_id: UUID,
    payload: DocumentTemplateCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentTemplateOut:
    app_result = await db.execute(
        select(Application).where(Application.id == application_id, Application.is_active.is_(True))
    )
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    template = DocumentTemplate(
        application_id=application_id,
        name=payload.name,
        description=payload.description,
        format=payload.format.lower(),
        detection=payload.detection,
        mapping=payload.mapping,
        validation=payload.validation,
        confidence_threshold=payload.confidence_threshold,
        created_by=current_user.id,
    )
    db.add(template)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="create",
        entity_type="document_template",
        entity_id=template.id,
        before_state=None,
        after_state={"application_id": str(application_id), "name": template.name},
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(template)
    return DocumentTemplateOut.model_validate(template)


@router.get("/{application_id}/templates", response_model=list[DocumentTemplateOut])
async def list_templates(
    application_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentTemplateOut]:
    result = await db.execute(
        select(DocumentTemplate)
        .where(
            DocumentTemplate.application_id == application_id,
            DocumentTemplate.is_active.is_(True),
        )
        .order_by(DocumentTemplate.created_at.desc())
    )
    return [DocumentTemplateOut.model_validate(item) for item in result.scalars().all()]


@router.put("/{application_id}/templates/{template_id}", response_model=DocumentTemplateOut)
async def update_template(
    application_id: UUID,
    template_id: UUID,
    payload: DocumentTemplateCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentTemplateOut:
    result = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.id == template_id,
            DocumentTemplate.application_id == application_id,
            DocumentTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    before = {
        "name": template.name,
        "mapping": template.mapping,
        "validation": template.validation,
    }

    for field, value in payload.model_dump().items():
        setattr(template, field, value)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="update",
        entity_type="document_template",
        entity_id=template.id,
        before_state=before,
        after_state=payload.model_dump(),
        request_id=get_request_id(request),
    )

    await db.commit()
    await db.refresh(template)
    return DocumentTemplateOut.model_validate(template)


@router.delete("/{application_id}/templates/{template_id}", response_model=MessageResponse)
async def delete_template(
    application_id: UUID,
    template_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    result = await db.execute(
        select(DocumentTemplate).where(
            DocumentTemplate.id == template_id,
            DocumentTemplate.application_id == application_id,
            DocumentTemplate.is_active.is_(True),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    template.is_active = False

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="delete",
        entity_type="document_template",
        entity_id=template.id,
        before_state={"is_active": True},
        after_state={"is_active": False},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Template archived")
