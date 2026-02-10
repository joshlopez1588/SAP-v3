from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models import User

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/trend")
async def trend_report(
    payload: dict,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {
        "report_type": "trend",
        "generated_at": datetime.now(UTC).isoformat(),
        "parameters": payload,
        "status": "queued",
    }


@router.post("/exceptions")
async def exceptions_report(
    payload: dict,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {
        "report_type": "exceptions",
        "generated_at": datetime.now(UTC).isoformat(),
        "parameters": payload,
        "status": "queued",
    }


@router.get("/{report_id}")
async def get_report(
    report_id: str,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {
        "id": report_id,
        "status": "ready",
        "download_url": f"/api/v1/reports/{report_id}/download",
    }


review_report_router = APIRouter(prefix="/reviews", tags=["review-reports"])


@review_report_router.post("/{review_id}/reports/review")
async def generate_review_report(
    review_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {"review_id": str(review_id), "report_type": "review", "status": "queued"}


@review_report_router.post("/{review_id}/reports/compliance")
async def generate_compliance_report(
    review_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {"review_id": str(review_id), "report_type": "compliance", "status": "queued"}


@review_report_router.post("/{review_id}/reports/evidence")
async def generate_evidence_package(
    review_id: UUID,
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {"review_id": str(review_id), "report_type": "evidence", "status": "queued"}
