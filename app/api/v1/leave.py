"""Leave and Holiday routes."""

from __future__ import annotations

import logging
import math
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import (
    get_current_admin,
    get_holiday_service,
    get_leave_service,
    get_optional_current_admin,
    require_admin,
)
from app.schemas.leave import (
    HolidayCreate,
    HolidayResponse,
    LeaveDecision,
    LeaveRequestCreate,
    LeaveRequestResponse,
)
from app.services.leave_service import HolidayService, LeaveService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["Leave & Holidays"])


# ── Leave endpoints ──────────────────────────────────────────────────────────

leave_router = APIRouter(prefix="/leave")


@leave_router.post(
    "",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit leave request",
    description=(
        "Submit a leave request. Can be submitted directly by employee (self-service) "
        "or by an administrator."
    ),
)
async def create_leave(
    data: LeaveRequestCreate,
    service: LeaveService = Depends(get_leave_service),
    current_admin: dict[str, Any] | None = Depends(get_optional_current_admin),
) -> dict[str, Any]:
    actor_id = current_admin["admin_id"] if current_admin else data.employee_id
    return await service.create_leave_request(data, actor_id=actor_id)


@leave_router.get(
    "",
    summary="List leave requests",
    description=(
        "Retrieve leave requests. Allows employees to check their leave status "
        "(filter by employee_id), or administrators to view all."
    ),
)
async def list_leave(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    employee_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    service: LeaveService = Depends(get_leave_service),
    current_admin: dict[str, Any] | None = Depends(get_optional_current_admin),
) -> dict[str, Any]:
    items, total = await service.list_leave_requests(
        page=page, page_size=page_size, employee_id=employee_id, status=status
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, math.ceil(total / page_size)),
    }


@leave_router.get(
    "/{leave_id}",
    response_model=LeaveRequestResponse,
    summary="Get leave request",
)
async def get_leave(
    leave_id: str,
    service: LeaveService = Depends(get_leave_service),
    current_admin: dict[str, Any] | None = Depends(get_optional_current_admin),
) -> dict[str, Any]:
    return await service.leave_repo.get_or_raise(leave_id)


@leave_router.patch(
    "/{leave_id}/approve",
    response_model=LeaveRequestResponse,
    summary="Approve leave request",
    description="Approve a pending leave request. Requires admin role.",
)
async def approve_leave(
    leave_id: str,
    decision: LeaveDecision,
    service: LeaveService = Depends(get_leave_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return await service.approve_leave(leave_id, decision, approver_id=current_admin["admin_id"])


@leave_router.patch(
    "/{leave_id}/reject",
    response_model=LeaveRequestResponse,
    summary="Reject leave request",
    description="Reject a pending leave request. Requires admin role.",
)
async def reject_leave(
    leave_id: str,
    decision: LeaveDecision,
    service: LeaveService = Depends(get_leave_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return await service.reject_leave(leave_id, decision, approver_id=current_admin["admin_id"])


# ── Holiday endpoints ─────────────────────────────────────────────────────────

holiday_router = APIRouter(prefix="/holidays")


@holiday_router.post(
    "",
    response_model=HolidayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create holiday",
    description="Add a company holiday. Requires admin role.",
)
async def create_holiday(
    data: HolidayCreate,
    service: HolidayService = Depends(get_holiday_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return await service.create_holiday(data)


@holiday_router.get(
    "",
    summary="List holidays",
)
async def list_holidays(
    service: HolidayService = Depends(get_holiday_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    items = await service.list_holidays()
    return {"items": items, "total": len(items)}
