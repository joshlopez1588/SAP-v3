from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, require_roles
from app.models import AIUsageLog, User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/providers")
async def list_providers(
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
) -> dict:
    return {
        "active": "mock",
        "providers": [
            {"name": "mock", "healthy": True, "classification": ["public", "internal", "confidential", "restricted"]},
            {"name": "azure_openai", "healthy": False, "classification": ["public", "internal", "confidential", "restricted"]},
            {"name": "openai", "healthy": False, "classification": ["public", "internal"]},
        ],
    }


@router.get("/usage")
async def usage_summary(
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    result = await db.execute(
        select(
            func.coalesce(func.sum(AIUsageLog.tokens_input), 0),
            func.coalesce(func.sum(AIUsageLog.tokens_output), 0),
            func.coalesce(func.sum(AIUsageLog.cost_estimate_usd), 0),
        )
    )
    tokens_in, tokens_out, cost = result.one()
    return {
        "tokens_input": int(tokens_in),
        "tokens_output": int(tokens_out),
        "cost_estimate_usd": float(cost),
    }


@router.get("/usage/history")
async def usage_history(
    _: Annotated[User, Depends(require_roles("admin", "analyst", "reviewer", "auditor", "examiner"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 200,
) -> dict:
    result = await db.execute(
        select(AIUsageLog)
        .order_by(AIUsageLog.created_at.desc())
        .limit(min(limit, 500))
    )

    return {
        "items": [
            {
                "id": str(item.id),
                "review_id": str(item.review_id) if item.review_id else None,
                "model_name": item.model_name,
                "function_type": item.function_type,
                "tokens_input": item.tokens_input,
                "tokens_output": item.tokens_output,
                "cost_estimate_usd": float(item.cost_estimate_usd or 0),
                "success": item.success,
                "created_at": item.created_at.isoformat(),
            }
            for item in result.scalars().all()
        ]
    }
