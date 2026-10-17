"""
Central Attendance Management System (CAMS) - Main Application.

Configures FastAPI, lifespan events (database connection, index initialization,
default tenant setup), correlation ID tracking, multi-tenant resolution, error handling,
CORS, and API routing.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.health import router as health_router
from app.api.v1.router import router as api_v1_router
from app.config import get_settings
from app.core.tenant import (
    DEFAULT_TENANT_ID,
    reset_current_tenant_id,
    set_current_tenant_id,
)
from app.database.connection import close_database_connection, connect_to_database, get_database
from app.database.indexes import create_indexes
from app.exceptions import CAMSError
from app.logging_config import setup_logging
from app.repositories.tenant_repo import TenantRepository

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting Central Attendance Management System (env: %s)...", settings.app_env)

    # 1. Connect to MongoDB and initialize indexes + default tenant
    try:
        await connect_to_database()
        db = get_database()
        await create_indexes(db)
        tenant_repo = TenantRepository(db)
        await tenant_repo.ensure_default_tenant()
    except Exception as exc:
        logger.warning(
            "Database connection deferred or unavailable on startup: %s. "
            "Readiness probe will report unavailable until connected.",
            exc,
        )

    yield

    # Graceful shutdown
    logger.info("Shutting down CAMS application...")
    await close_database_connection()
    logger.info("Application shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description=(
            "Enterprise-grade Central Attendance Management System API with multi-tenancy, "
            "deterministic policy evaluation, multi-session tracking, and automated monitoring."
        ),
        version="1.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS Middleware ───────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.app_env != "production" else ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Request / Correlation & Tenant Context Middleware ──────────────────────────
    @app.middleware("http")
    async def tenant_and_correlation_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        # Resolve tenant identifier
        tenant_id = request.headers.get("X-Tenant-ID") or DEFAULT_TENANT_ID
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from app.security.auth import decode_access_token

                payload = decode_access_token(auth_header[7:].strip())
                if payload.get("tenant_id"):
                    tenant_id = str(payload["tenant_id"])
            except Exception:
                pass

        token = set_current_tenant_id(tenant_id)
        request.state.tenant_id = tenant_id

        start_time = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            reset_current_tenant_id(token)

        process_time = time.perf_counter() - start_time

        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Tenant-ID"] = tenant_id
        response.headers["X-Process-Time"] = f"{process_time:.4f}s"
        return response

    # ── Global Exception Handlers ────────────────────────────────────────────────
    @app.exception_handler(CAMSError)
    async def cams_error_handler(request: Request, exc: CAMSError) -> JSONResponse:
        logger.warning(
            "Application error [%s]: %s (path: %s)",
            exc.__class__.__name__,
            exc.detail,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.__class__.__name__,
                "detail": exc.detail,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = [
            {
                "loc": list(err.get("loc", [])),
                "msg": err.get("msg", ""),
                "type": err.get("type", ""),
            }
            for err in exc.errors()
        ]
        logger.info("Validation error on %s: %s", request.url.path, errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "detail": "Request body or query parameter validation failed.",
                "errors": errors,
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

    # ── Static Files (Documentation Viewer) ──────────────────────────────────────
    static_dir = Path(__file__).resolve().parent.parent / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/dashboard", include_in_schema=False)
    @app.get("/app", include_in_schema=False)
    async def dashboard() -> FileResponse:
        return FileResponse(str(static_dir / "index.html"))

    @app.get("/", tags=["Root"])
    async def root(request: Request):
        accept = request.headers.get("accept", "")
        if "text/html" in accept and static_dir.exists():
            return FileResponse(str(static_dir / "index.html"))
        return {
            "app": settings.app_name,
            "version": "1.1.0",
            "environment": settings.app_env,
            "docs": "/docs",
            "dashboard": "/dashboard",
        }

    # ── Routers ───────────────────────────────────────────────────────────────────
    app.include_router(health_router, prefix="/health")
    app.include_router(health_router, prefix="/api/v1/health")
    app.include_router(api_v1_router)

    return app


app = create_app()
