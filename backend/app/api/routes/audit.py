from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models import AuditLog, User
from app.schemas.audit import AuditEntryOut, AuditVerificationResponse
from app.services.audit_service import verify_audit_hash_chain

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditEntryOut])
async def list_audit_entries(
    _: Annotated[User, Depends(require_roles("admin", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    entity_type: str | None = None,
    action: str | None = None,
    limit: int = 200,
) -> list[AuditEntryOut]:
    query = select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(min(limit, 500))
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if action:
        query = query.where(AuditLog.action == action)

    result = await db.execute(query)
    return [AuditEntryOut.model_validate(item) for item in result.scalars().all()]


@router.post("/verify", response_model=AuditVerificationResponse)
async def verify_chain(
    _: Annotated[User, Depends(require_roles("admin", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AuditVerificationResponse:
    result = await verify_audit_hash_chain(db)
    return AuditVerificationResponse(
        valid=result.valid,
        checked_entries=result.checked_entries,
        first_invalid_id=result.first_invalid_id,
        message=result.message,
    )


@router.get("/stats")
async def audit_stats(
    _: Annotated[User, Depends(require_roles("admin", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, int | str]:
    total_result = await db.execute(select(func.count()).select_from(AuditLog))
    total = int(total_result.scalar() or 0)

    latest_result = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    latest = latest_result.scalar_one_or_none()

    return {
        "entries": total,
        "last_entry_at": latest.timestamp.isoformat() if latest else "",
    }


@router.get("/export")
async def export_audit(
    _: Annotated[User, Depends(require_roles("admin", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    fmt: str = "json",
):
    result = await db.execute(select(AuditLog).order_by(AuditLog.id.asc()))
    entries = list(result.scalars().all())

    if fmt.lower() == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "timestamp", "actor_id", "action", "entity_type", "entity_id", "content_hash", "previous_hash"])
        for entry in entries:
            writer.writerow(
                [
                    entry.id,
                    entry.timestamp.isoformat(),
                    str(entry.actor_id) if entry.actor_id else "",
                    entry.action,
                    entry.entity_type,
                    str(entry.entity_id) if entry.entity_id else "",
                    entry.content_hash,
                    entry.previous_hash or "",
                ]
            )

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit-{datetime.utcnow().date().isoformat()}.csv"},
        )

    payload = [
        {
            "id": entry.id,
            "timestamp": entry.timestamp.isoformat(),
            "actor_id": str(entry.actor_id) if entry.actor_id else None,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": str(entry.entity_id) if entry.entity_id else None,
            "content_hash": entry.content_hash,
            "previous_hash": entry.previous_hash,
            "metadata": entry.metadata,
        }
        for entry in entries
    ]
    return payload
