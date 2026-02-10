from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.utils.serialization import to_jsonable


@dataclass
class AuditVerificationResult:
    valid: bool
    checked_entries: int
    first_invalid_id: int | None
    message: str


def _canonical_hash_payload(payload: dict[str, Any]) -> str:
    normalized = to_jsonable(payload)
    raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def record_audit_event(
    db: AsyncSession,
    *,
    actor_id: UUID | None,
    actor_type: str,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    before_state: dict[str, Any] | None,
    after_state: dict[str, Any] | None,
    request_id: str | None,
    metadata: dict[str, Any] | None = None,
) -> AuditLog:
    latest = await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(1))
    previous = latest.scalar_one_or_none()
    previous_hash = previous.content_hash if previous else None

    payload = {
        "actor_id": str(actor_id) if actor_id else None,
        "actor_type": actor_type,
        "action": action,
        "entity_type": entity_type,
        "entity_id": str(entity_id) if entity_id else None,
        "before_state": before_state,
        "after_state": after_state,
        "metadata": metadata or {},
        "request_id": request_id,
        "previous_hash": previous_hash,
    }
    content_hash = _canonical_hash_payload(payload)

    entry = AuditLog(
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before_state=before_state,
        after_state=after_state,
        audit_metadata=metadata or {},
        request_id=request_id,
        previous_hash=previous_hash,
        content_hash=content_hash,
    )
    db.add(entry)
    await db.flush()
    return entry


async def verify_audit_hash_chain(db: AsyncSession) -> AuditVerificationResult:
    result = await db.execute(select(AuditLog).order_by(AuditLog.id.asc()))
    entries = list(result.scalars().all())

    previous_hash: str | None = None
    for entry in entries:
        payload = {
            "actor_id": str(entry.actor_id) if entry.actor_id else None,
            "actor_type": entry.actor_type,
            "action": entry.action,
            "entity_type": entry.entity_type,
            "entity_id": str(entry.entity_id) if entry.entity_id else None,
            "before_state": entry.before_state,
            "after_state": entry.after_state,
            "metadata": entry.audit_metadata,
            "request_id": entry.request_id,
            "previous_hash": previous_hash,
        }
        expected_hash = _canonical_hash_payload(payload)

        if entry.previous_hash != previous_hash:
            return AuditVerificationResult(
                valid=False,
                checked_entries=len(entries),
                first_invalid_id=entry.id,
                message=f"Previous hash mismatch at entry {entry.id}",
            )
        if entry.content_hash != expected_hash:
            return AuditVerificationResult(
                valid=False,
                checked_entries=len(entries),
                first_invalid_id=entry.id,
                message=f"Content hash mismatch at entry {entry.id}",
            )
        previous_hash = entry.content_hash

    return AuditVerificationResult(
        valid=True,
        checked_entries=len(entries),
        first_invalid_id=None,
        message="Hash chain verified",
    )
