"""FastAPI dependency injection — services, DB access, and auth."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database.connection import get_database
from app.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from app.repositories.admin_repo import AdminRepository, AuditRepository, NotificationRepository
from app.repositories.attendance_repo import AttendanceRepository
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.leave_repo import HolidayRepository, LeaveRepository
from app.security.auth import decode_access_token
from app.services.attendance_service import AttendanceService
from app.services.audit_service import AuditService
from app.services.employee_service import EmployeeService
from app.services.leave_service import HolidayService, LeaveService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# ── DB-backed repo factories ──────────────────────────────────────────────────


def get_employee_repo(db: Any = Depends(get_database)) -> EmployeeRepository:
    return EmployeeRepository(db)


def get_attendance_repo(db: Any = Depends(get_database)) -> AttendanceRepository:
    return AttendanceRepository(db)


def get_leave_repo(db: Any = Depends(get_database)) -> LeaveRepository:
    return LeaveRepository(db)


def get_holiday_repo(db: Any = Depends(get_database)) -> HolidayRepository:
    return HolidayRepository(db)


def get_admin_repo(db: Any = Depends(get_database)) -> AdminRepository:
    return AdminRepository(db)


def get_audit_repo(db: Any = Depends(get_database)) -> AuditRepository:
    return AuditRepository(db)


def get_notification_repo(db: Any = Depends(get_database)) -> NotificationRepository:
    return NotificationRepository(db)


# ── Service factories ─────────────────────────────────────────────────────────


def get_audit_service(
    repo: AuditRepository = Depends(get_audit_repo),
) -> AuditService:
    return AuditService(repo)


def get_employee_service(
    repo: EmployeeRepository = Depends(get_employee_repo),
) -> EmployeeService:
    return EmployeeService(repo)


def get_notification_service() -> NotificationService:
    return NotificationService()


def get_attendance_service(
    attendance_repo: AttendanceRepository = Depends(get_attendance_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    audit_service: AuditService = Depends(get_audit_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> AttendanceService:
    from app.config import get_settings

    settings = get_settings()
    return AttendanceService(
        attendance_repo=attendance_repo,
        employee_repo=employee_repo,
        audit_service=audit_service,
        notification_service=notification_service,
        company_tz=settings.company_timezone,
    )


def get_leave_service(
    leave_repo: LeaveRepository = Depends(get_leave_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    audit_service: AuditService = Depends(get_audit_service),
) -> LeaveService:
    return LeaveService(
        leave_repo=leave_repo,
        employee_repo=employee_repo,
        audit_service=audit_service,
    )


def get_holiday_service(
    holiday_repo: HolidayRepository = Depends(get_holiday_repo),
) -> HolidayService:
    return HolidayService(holiday_repo)


def get_report_service(
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    attendance_repo: AttendanceRepository = Depends(get_attendance_repo),
    leave_service: LeaveService = Depends(get_leave_service),
    holiday_service: HolidayService = Depends(get_holiday_service),
) -> ReportService:
    return ReportService(
        employee_repo=employee_repo,
        attendance_repo=attendance_repo,
        leave_service=leave_service,
        holiday_service=holiday_service,
    )


# ── Authentication ────────────────────────────────────────────────────────────


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    admin_repo: AdminRepository = Depends(get_admin_repo),
) -> dict[str, Any]:
    """Validate JWT and return the current admin user document."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenExpiredError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or malformed token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    admin_id = payload.get("sub")
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    admin = await admin_repo.find_by_id(admin_id)
    if admin is None or not admin.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found or inactive.",
        )

    return admin


async def get_optional_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    admin_repo: AdminRepository = Depends(get_admin_repo),
) -> dict[str, Any] | None:
    """Validate JWT if provided, otherwise return None (allows self-service endpoints)."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        admin_id = payload.get("sub")
        if not admin_id:
            return None
        return await admin_repo.find_by_id(admin_id)
    except Exception:
        return None


def require_role(*roles: str):
    """Dependency factory that enforces role-based access control."""

    async def role_checker(
        current_admin: dict[str, Any] = Depends(get_current_admin),
    ) -> dict[str, Any]:
        if current_admin["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {', '.join(roles)}. Your role: {current_admin['role']}.",
            )
        return current_admin

    return role_checker


# Convenience aliases
require_admin = require_role("admin", "super_admin")
require_super_admin = require_role("super_admin")
