"""Admin management and monitoring trigger routes."""

from __future__ import annotations

import logging
import math
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_admin_repo,
    get_audit_repo,
    get_audit_service,
    require_admin,
)
from app.exceptions import ConflictError
from app.repositories.admin_repo import AdminRepository, AuditRepository
from app.schemas.auth import AdminCreate, AdminResponse
from app.security.password import hash_password
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Administration"])


@router.post(
    "/users",
    response_model=AdminResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new administrator or manager",
    description="Provision a new admin or manager user account. Requires admin role.",
)
async def create_admin_user(
    data: AdminCreate,
    admin_repo: AdminRepository = Depends(get_admin_repo),
    audit_service: AuditService = Depends(get_audit_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    # Check for existing username
    existing_username = await admin_repo.find_by_username(data.username)
    if existing_username is not None:
        raise ConflictError(f"Admin username '{data.username}' is already taken.")

    # Check for existing email
    existing_email = await admin_repo.find_by_email(data.email)
    if existing_email is not None:
        raise ConflictError(f"Admin email '{data.email}' is already registered.")

    now = datetime.now(tz=UTC)
    admin_id = f"ADM-{uuid.uuid4().hex[:8].upper()}"

    doc = {
        "admin_id": admin_id,
        "username": data.username,
        "email": data.email.lower(),
        "hashed_password": hash_password(data.password),
        "role": data.role,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }

    created = await admin_repo.create(doc)
    logger.info(
        "Admin user '%s' (%s) created by %s",
        data.username,
        admin_id,
        current_admin["username"],
    )

    await audit_service.log(
        actor_id=current_admin["admin_id"],
        action="admin.create",
        resource_type="admin_user",
        resource_id=admin_id,
        new_values={"username": data.username, "email": data.email, "role": data.role},
    )

    safe = {k: v for k, v in created.items() if k != "hashed_password"}
    return safe


@router.get(
    "/users",
    response_model=list[AdminResponse],
    summary="List administrators and managers",
    description="Retrieve all registered administrator and manager accounts. Requires admin role.",
)
async def list_admin_users(
    admin_repo: AdminRepository = Depends(get_admin_repo),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    return await admin_repo.list_admins()


@router.get(
    "/audit-logs",
    summary="List audit logs",
    description="Retrieve audit logs. Requires admin role.",
)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    resource_type: str | None = Query(default=None),
    actor_id: str | None = Query(default=None),
    employee_id: str | None = Query(default=None),
    audit_repo: AuditRepository = Depends(get_audit_repo),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    skip = (page - 1) * page_size
    items, total = await audit_repo.list_logs(
        skip=skip,
        limit=page_size,
        resource_type=resource_type,
        actor_id=actor_id,
        employee_id=employee_id,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


@router.post(
    "/monitoring/run",
    summary="Trigger monitoring cycle",
    description=(
        "Manually trigger an attendance monitoring cycle. "
        "Evaluates policy compliance (min 3 days/week, min 15 hrs/week, min 5 hrs/day average) "
        "and sends violation alert emails. Accessible by admin role."
    ),
    status_code=status.HTTP_200_OK,
)
async def trigger_monitoring(
    include_current_week: bool = Query(
        default=True,
        description="Include current week for immediate evaluation (useful for testing).",
    ),
    force_resend: bool = Query(
        default=True,
        description="Force sending email alerts even if already sent earlier (useful for testing).",
    ),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    from app.database.connection import get_database
    from app.workers.monitoring import run_monitoring_cycle

    db = get_database()
    result = await run_monitoring_cycle(
        db,
        include_current_week=include_current_week,
        force_resend=force_resend,
    )
    return {"message": "Monitoring cycle completed.", "result": result}
