"""Tenant management endpoints (/api/v1/tenants) for multi-tenant onboarding and configuration."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_admin_repo, get_tenant_repo, require_admin
from app.repositories.admin_repo import AdminRepository
from app.repositories.tenant_repo import TenantNotFoundError, TenantRepository
from app.schemas.tenant import (
    TenantCreateRequest,
    TenantResponse,
    TenantUpdateRequest,
)
from app.security.password import hash_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tenants", tags=["Tenants & Multi-Tenancy"])


@router.post(
    "",
    response_model=TenantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Onboard new tenant organization (Admin / Super-Admin only)",
    description="Provision a new tenant organization with isolated attendance and policy configs.",
)
async def onboard_tenant(
    data: TenantCreateRequest,
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    admin_repo: AdminRepository = Depends(get_admin_repo),
    _current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    existing = await tenant_repo.find_by_id(data.tenant_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant '{data.tenant_id}' already exists.",
        )

    doc = {
        "tenant_id": data.tenant_id.lower().strip(),
        "name": data.name.strip(),
        "contact_email": data.contact_email.lower().strip(),
        "status": "active",
        "settings": data.settings.model_dump(),
    }
    created = await tenant_repo.create(doc)
    logger.info("Onboarded new tenant organization: '%s'", data.tenant_id)

    # If initial admin credentials are provided, provision tenant admin immediately
    if data.admin_username and data.admin_password:
        admin_repo.tenant_id = data.tenant_id.lower().strip()
        admin_doc = {
            "admin_id": f"ADM-{uuid.uuid4().hex[:8].upper()}",
            "username": data.admin_username.strip(),
            "email": data.contact_email.lower().strip(),
            "name": f"{data.name.strip()} Administrator",
            "hashed_password": hash_password(data.admin_password),
            "role": "admin",
            "is_active": True,
            "tenant_id": data.tenant_id.lower().strip(),
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        await admin_repo.create(admin_doc)
        logger.info(
            "Created initial admin '%s' for tenant '%s'.",
            data.admin_username,
            data.tenant_id,
        )

    return created


@router.get(
    "",
    response_model=list[TenantResponse],
    summary="List all tenant organizations",
    description="Returns all registered tenant organizations (Admin access required).",
)
async def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    _current_admin: dict[str, Any] = Depends(require_admin),
) -> list[dict[str, Any]]:
    items, _ = await tenant_repo.list_tenants(skip=skip, limit=limit, status=status_filter)
    return items


@router.get(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Get tenant organization details",
    description="Retrieve details and policy configuration for a specific tenant.",
)
async def get_tenant(
    tenant_id: str,
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
) -> dict[str, Any]:
    try:
        return await tenant_repo.get_or_raise(tenant_id)
    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found.",
        ) from None


@router.put(
    "/{tenant_id}",
    response_model=TenantResponse,
    summary="Update tenant organization configuration",
    description="Modify tenant settings, timezone, shift schedules, or organization status.",
)
async def update_tenant(
    tenant_id: str,
    data: TenantUpdateRequest,
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
    _current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    update_data = dict(data.model_dump(exclude_unset=True))
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )

    try:
        updated = await tenant_repo.update(tenant_id, update_data)
        logger.info("Updated configuration for tenant '%s'", tenant_id)
        return updated
    except TenantNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tenant '{tenant_id}' not found.",
        ) from None
