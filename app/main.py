"""
Central Attendance Management System (CAMS) - Main Application.

Configures FastAPI, lifespan events (database connection & index initialization),
correlation ID tracking, error handling, CORS, and API routing.
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
from app.database.connection import close_database_connection, connect_to_database, get_database
from app.database.indexes import create_indexes
from app.exceptions import CAMSError
from app.logging_config import setup_logging

logger = logging.getLogger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    settings = get_settings()
    setup_logging(settings.log_level)
    logger.info("Starting Central Attendance Management System (env: %s)...", settings.app_env)

    # 1. Connect to MongoDB
    await connect_to_database()

    # 2. Ensure indexes are created
    try:
        db = get_database()
        await create_indexes(db)
    except Exception as exc:
        logger.error("Failed to initialize database indexes: %s", exc)

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
            "Enterprise-grade Central Attendance Management System API with deterministic "
            "policy evaluation, multi-session tracking, leave workflows, and automated monitoring."
        ),
        version="1.0.0",
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

    # ── Request / Correlation Middleware ──────────────────────────────────────────
    @app.middleware("http")
    async def correlation_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.state.correlation_id = correlation_id

        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time

        response.headers["X-Correlation-ID"] = correlation_id
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
        logger.warning("Validation error on %s: %s", request.url.path, exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "ValidationError",
                "detail": "Request validation failed",
                "errors": exc.errors(),
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "InternalServerError",
                "detail": "An internal server error occurred.",
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )

    # ── Root & Static Dashboard Routes ──────────────────────────────────────────
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
        # Browser navigation gets the executive frontend directly
        if "text/html" in accept and static_dir.exists():
            return FileResponse(str(static_dir / "index.html"))
        return {
            "app": settings.app_name,
            "version": "1.0.0",
            "environment": settings.app_env,
            "docs": "/docs",
            "dashboard": "/dashboard",
        }

    # Mount health checks under both /health and /api/v1/health
    app.include_router(health_router, prefix="/health")
    app.include_router(health_router, prefix="/api/v1/health")

    # Mount API v1 router
    app.include_router(api_v1_router)

    return app


app = create_app()
