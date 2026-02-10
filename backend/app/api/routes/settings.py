from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import require_roles
from app.models import User

router = APIRouter(prefix="/settings", tags=["settings"])

# POC in-memory settings cache; production should persist this in DB.
SYSTEM_SETTINGS: dict[str, object] = {
    "session_timeout_minutes": 30,
    "max_concurrent_sessions": 3,
    "password_min_length": 12,
    "ai_enabled": True,
    "ai_model": "mock",
    "ai_temperature": 0.2,
    "default_confidence_threshold": 0.95,
    "max_file_size_mb": 50,
}


@router.get("")
async def get_settings(_: Annotated[User, Depends(require_roles("admin", "reviewer", "analyst", "auditor", "examiner"))]) -> dict[str, object]:
    return SYSTEM_SETTINGS


@router.put("")
async def update_settings(
    payload: dict[str, object],
    _: Annotated[User, Depends(require_roles("admin"))],
) -> dict[str, object]:
    SYSTEM_SETTINGS.update(payload)
    return SYSTEM_SETTINGS


@router.get("/ai")
async def get_ai_settings(
    _: Annotated[User, Depends(require_roles("admin", "reviewer", "analyst"))],
) -> dict[str, object]:
    return {
        "providers": ["mock", "azure_openai", "openai", "anthropic", "google", "bedrock", "ollama"],
        "active_provider": "mock",
        "routing": {
            "description": "mock",
            "remediation": "mock",
            "summary": "mock",
        },
        "fallback_chain": ["mock"],
    }


@router.put("/ai")
async def update_ai_settings(
    payload: dict[str, object],
    _: Annotated[User, Depends(require_roles("admin"))],
) -> dict[str, object]:
    SYSTEM_SETTINGS.update({"ai_config": payload})
    return {"message": "AI settings updated", "ai_config": payload}
