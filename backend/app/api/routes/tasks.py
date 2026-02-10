from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models import User

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task(
    task_id: str,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {
        "id": task_id,
        "type": "analysis",
        "status": "completed",
        "progress": 100,
        "started_at": datetime.now(UTC).isoformat(),
        "completed_at": datetime.now(UTC).isoformat(),
        "error_message": None,
        "review_id": None,
    }
