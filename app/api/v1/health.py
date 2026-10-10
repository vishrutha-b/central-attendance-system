"""Health check endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Response, status

from app.database.connection import get_database

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Health"])


@router.get(
    "/live",
    summary="Liveness probe",
    description="Returns 200 if the process is running.",
    response_model=dict,
)
async def liveness() -> dict[str, str]:
    return {"status": "ok", "message": "Service is alive."}


@router.get(
    "/ready",
    summary="Readiness probe",
    description="Returns 200 if the service can accept requests (DB reachable).",
    response_model=dict,
)
async def readiness(response: Response) -> dict[str, Any]:
    try:
        db = get_database()
        await db.command("ping")
        return {"status": "ready", "database": "connected"}
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "database": "unavailable"}
