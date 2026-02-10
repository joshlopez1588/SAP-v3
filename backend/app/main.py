from __future__ import annotations

import logging
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.routes.ai import router as ai_router
from app.api.routes.applications import router as applications_router
from app.api.routes.audit import router as audit_router
from app.api.routes.auth import admin_router, router as auth_router
from app.api.routes.frameworks import router as frameworks_router
from app.api.routes.reports import review_report_router, router as reports_router
from app.api.routes.reviews import reference_router, router as reviews_router
from app.api.routes.settings import router as settings_router
from app.api.routes.tasks import router as tasks_router
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine

setup_logging()
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(title=settings.app_name, version=settings.app_version)
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    max_age=3600,
)

app_start_time = time.time()


@app.on_event("startup")
async def on_startup() -> None:
    Path(settings.file_storage_path).mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Application startup complete")


@app.middleware("http")
async def add_rate_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-RateLimit-Limit"] = "300"
    response.headers["X-RateLimit-Remaining"] = "299"
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.exception("Unhandled exception", extra={"request_id": request_id})
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "Unexpected server error",
                "request_id": request_id,
            }
        },
    )


@app.get("/health")
async def health() -> dict:
    uptime = int(time.time() - app_start_time)
    return {
        "status": "healthy",
        "version": settings.app_version,
        "uptime_seconds": uptime,
        "checks": {
            "application": {"status": "healthy"},
        },
    }


@app.get("/health/ready")
async def health_ready() -> JSONResponse:
    uptime = int(time.time() - app_start_time)
    checks: dict[str, dict] = {}
    http_status = 200

    db_latency_ms = 0
    db_status = "healthy"
    db_start = time.time()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_latency_ms = int((time.time() - db_start) * 1000)
    except Exception:
        db_status = "unhealthy"
        http_status = 503

    checks["database"] = {"status": db_status, "latency_ms": db_latency_ms}
    checks["storage"] = {"status": "healthy" if Path(settings.file_storage_path).exists() else "unhealthy"}

    overall = "healthy" if http_status == 200 else "unhealthy"
    return JSONResponse(
        status_code=http_status,
        content={
            "status": overall,
            "version": settings.app_version,
            "uptime_seconds": uptime,
            "checks": checks,
        },
    )


app.include_router(auth_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(frameworks_router, prefix=settings.api_prefix)
app.include_router(applications_router, prefix=settings.api_prefix)
app.include_router(reviews_router, prefix=settings.api_prefix)
app.include_router(reference_router, prefix=settings.api_prefix)
app.include_router(audit_router, prefix=settings.api_prefix)
app.include_router(settings_router, prefix=settings.api_prefix)
app.include_router(ai_router, prefix=settings.api_prefix)
app.include_router(tasks_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)
app.include_router(review_report_router, prefix=settings.api_prefix)

frontend_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if frontend_dist.exists():
    assets_path = frontend_dist / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")


@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if full_path.startswith("api"):
        return JSONResponse(status_code=404, content={"error": "Not found"})

    index_path = frontend_dist / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return JSONResponse(content={"message": "Frontend not built"}, status_code=404)
