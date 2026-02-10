from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_request_id, require_roles
from app.models import Framework, User
from app.schemas.framework import (
    FrameworkCreate,
    FrameworkOut,
    FrameworkPublishResponse,
    FrameworkUpdate,
)
from app.schemas.common import MessageResponse
from app.services.audit_service import record_audit_event

router = APIRouter(prefix="/frameworks", tags=["frameworks"])


@router.get("", response_model=list[FrameworkOut])
async def list_frameworks(
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    review_type: str | None = None,
) -> list[FrameworkOut]:
    query = select(Framework).where(Framework.is_active.is_(True)).order_by(Framework.created_at.desc())
    if review_type:
        query = query.where(Framework.review_type == review_type)
    result = await db.execute(query)
    return [FrameworkOut.model_validate(item) for item in result.scalars().all()]


@router.post("", response_model=FrameworkOut)
async def create_framework(
    payload: FrameworkCreate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameworkOut:
    framework = Framework(
        name=payload.name,
        description=payload.description,
        review_type=payload.review_type,
        settings=payload.settings,
        checks=payload.checks,
        regulatory_mappings=payload.regulatory_mappings,
        effective_date=payload.effective_date,
        created_by=current_user.id,
    )
    db.add(framework)
    await db.flush()

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="create",
        entity_type="framework",
        entity_id=framework.id,
        before_state=None,
        after_state={"name": framework.name, "review_type": framework.review_type},
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(framework)
    return FrameworkOut.model_validate(framework)


@router.get("/{framework_id}", response_model=FrameworkOut)
async def get_framework(
    framework_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameworkOut:
    result = await db.execute(select(Framework).where(Framework.id == framework_id, Framework.is_active.is_(True)))
    framework = result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")
    return FrameworkOut.model_validate(framework)


@router.put("/{framework_id}", response_model=FrameworkOut)
async def update_framework(
    framework_id: UUID,
    payload: FrameworkUpdate,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameworkOut:
    result = await db.execute(select(Framework).where(Framework.id == framework_id, Framework.is_active.is_(True)))
    framework = result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    if framework.is_immutable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="FRAMEWORK_IMMUTABLE")

    before = {
        "name": framework.name,
        "description": framework.description,
        "settings": framework.settings,
        "checks": framework.checks,
        "regulatory_mappings": framework.regulatory_mappings,
    }

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(framework, field, value)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="update",
        entity_type="framework",
        entity_id=framework.id,
        before_state=before,
        after_state=payload.model_dump(exclude_unset=True),
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(framework)
    return FrameworkOut.model_validate(framework)


@router.delete("/{framework_id}", response_model=MessageResponse)
async def soft_delete_framework(
    framework_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    result = await db.execute(select(Framework).where(Framework.id == framework_id, Framework.is_active.is_(True)))
    framework = result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    framework.is_active = False

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="delete",
        entity_type="framework",
        entity_id=framework.id,
        before_state={"is_active": True},
        after_state={"is_active": False},
        request_id=get_request_id(request),
    )
    await db.commit()
    return MessageResponse(message="Framework archived")


@router.post("/{framework_id}/publish", response_model=FrameworkPublishResponse)
async def publish_framework(
    framework_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameworkPublishResponse:
    result = await db.execute(select(Framework).where(Framework.id == framework_id, Framework.is_active.is_(True)))
    framework = result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    if framework.status == "published" and framework.is_immutable:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Framework already published")

    framework.status = "published"
    framework.is_immutable = True

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="publish",
        entity_type="framework",
        entity_id=framework.id,
        before_state={"status": "draft"},
        after_state={"status": framework.status, "immutable": framework.is_immutable},
        request_id=get_request_id(request),
    )
    await db.commit()

    return FrameworkPublishResponse(
        id=framework.id,
        version_label=f"{framework.version_major}.{framework.version_minor}.{framework.version_patch}",
        status=framework.status,
    )


@router.post("/{framework_id}/clone", response_model=FrameworkOut)
async def clone_framework(
    framework_id: UUID,
    request: Request,
    current_user: Annotated[User, Depends(require_roles("admin", "analyst"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> FrameworkOut:
    result = await db.execute(select(Framework).where(Framework.id == framework_id, Framework.is_active.is_(True)))
    framework = result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    clone = Framework(
        name=f"{framework.name} (Clone)",
        description=framework.description,
        review_type=framework.review_type,
        version_major=framework.version_major,
        version_minor=framework.version_minor,
        version_patch=framework.version_patch + 1,
        settings=framework.settings,
        checks=framework.checks,
        regulatory_mappings=framework.regulatory_mappings,
        status="draft",
        is_immutable=False,
        parent_framework_id=framework.id,
        created_by=current_user.id,
    )
    db.add(clone)

    await record_audit_event(
        db,
        actor_id=current_user.id,
        actor_type="USER",
        action="clone",
        entity_type="framework",
        entity_id=clone.id,
        before_state={"source_framework_id": str(framework.id)},
        after_state={"name": clone.name},
        request_id=get_request_id(request),
    )
    await db.commit()
    await db.refresh(clone)
    return FrameworkOut.model_validate(clone)


@router.get("/{framework_id}/versions", response_model=list[FrameworkOut])
async def framework_versions(
    framework_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[FrameworkOut]:
    target_result = await db.execute(select(Framework).where(Framework.id == framework_id, Framework.is_active.is_(True)))
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    result = await db.execute(
        select(Framework)
        .where(Framework.name == target.name, Framework.is_active.is_(True))
        .order_by(Framework.version_major.desc(), Framework.version_minor.desc(), Framework.version_patch.desc())
    )
    return [FrameworkOut.model_validate(item) for item in result.scalars().all()]


@router.post("/{framework_id}/test")
async def test_framework(
    framework_id: UUID,
    payload: dict[str, Any],
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    result = await db.execute(select(Framework).where(Framework.id == framework_id, Framework.is_active.is_(True)))
    framework = result.scalar_one_or_none()
    if not framework:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Framework not found")

    records = payload.get("records", [])
    matched: list[dict[str, Any]] = []

    for check in framework.checks:
        if not check.get("enabled", True):
            continue
        condition = check.get("condition", {})
        field = condition.get("field")
        op = condition.get("operator")
        value = condition.get("value")

        if field and op == "equals":
            check_matches = [r for r in records if r.get(field) == value]
            if check_matches:
                matched.append({"check_id": check.get("id"), "match_count": len(check_matches)})

    return {"framework_id": str(framework.id), "matched_checks": matched, "record_count": len(records)}
