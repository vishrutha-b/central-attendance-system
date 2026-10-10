"""Attendance recording and history routes."""

from __future__ import annotations

import logging
import math
from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import get_attendance_service, get_current_admin, require_admin
from app.schemas.attendance import (
    AttendanceCorrection,
    AttendanceEntryRequest,
    AttendanceExitRequest,
    AttendanceQuickRecordRequest,
    AttendanceSessionResponse,
)
from app.services.attendance_service import AttendanceService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _check_employee_access(current_admin: dict[str, Any], emp_id: str) -> None:
    if current_admin.get("role") == "employee":
        my_id = (current_admin.get("employee_id") or current_admin.get("admin_id") or "").upper()
        if emp_id.upper() != my_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Employees can only access their own attendance records.",
            )


@router.post(
    "/entry",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record entry",
    description=(
        "Record an employee's office entry time. " "Fails if there is already an open session."
    ),
)
async def record_entry(
    data: AttendanceEntryRequest,
    service: AttendanceService = Depends(get_attendance_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    _check_employee_access(current_admin, data.employee_id)
    return await service.record_entry(data, actor_id=current_admin["admin_id"])


@router.post(
    "/exit",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_200_OK,
    summary="Record exit",
    description=(
        "Record an employee's office exit time. "
        "Closes the open session and calculates total hours."
    ),
)
async def record_exit(
    data: AttendanceExitRequest,
    service: AttendanceService = Depends(get_attendance_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    _check_employee_access(current_admin, data.employee_id)
    return await service.record_exit(data, actor_id=current_admin["admin_id"])


@router.post(
    "/quick-record",
    response_model=AttendanceSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Quick attendance record",
    description=(
        "Record a complete attendance session (entry + exit) in one step. "
        "Provide employee_id, optional date (defaults to today), "
        "optional entry_time (e.g. '09:00', defaults to 09:00), "
        "and optional exit_time (e.g. '18:00', defaults to 18:00)."
    ),
)
async def quick_record(
    data: AttendanceQuickRecordRequest,
    service: AttendanceService = Depends(get_attendance_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    _check_employee_access(current_admin, data.employee_id)
    return await service.quick_record(data, actor_id=current_admin["admin_id"])


@router.get(
    "/{employee_id}",
    summary="Get attendance for a specific date",
    description="Retrieve all attendance sessions for an employee on a given date.",
)
async def get_attendance_by_date(
    employee_id: str,
    date: date = Query(..., description="Date in YYYY-MM-DD format"),
    service: AttendanceService = Depends(get_attendance_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    _check_employee_access(current_admin, employee_id)
    sessions = await service.get_attendance_for_date(employee_id, date.isoformat())
    return {"employee_id": employee_id.upper(), "date": date.isoformat(), "sessions": sessions}


@router.get(
    "/{employee_id}/history",
    summary="Get attendance history",
    description="Retrieve paginated attendance history for an employee.",
)
async def get_attendance_history(
    employee_id: str,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    service: AttendanceService = Depends(get_attendance_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    _check_employee_access(current_admin, employee_id)
    items, total = await service.get_attendance_history(
        employee_id=employee_id,
        page=page,
        page_size=page_size,
        start_date=start_date,
        end_date=end_date,
    )
    total_pages = max(1, math.ceil(total / page_size))
    return {
        "employee_id": employee_id.upper(),
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.patch(
    "/session/{attendance_id}",
    response_model=AttendanceSessionResponse,
    summary="Correct attendance",
    description=(
        "Administratively correct an attendance record's entry or exit time. "
        "Creates an audit log entry. Requires admin role."
    ),
)
async def correct_attendance(
    attendance_id: str,
    data: AttendanceCorrection,
    service: AttendanceService = Depends(get_attendance_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return await service.correct_attendance(
        attendance_id=attendance_id,
        data=data,
        actor_id=current_admin["admin_id"],
    )
