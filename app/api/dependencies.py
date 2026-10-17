"""FastAPI dependency injection — services, DB access, multi-tenancy, and auth."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.tenant import DEFAULT_TENANT_ID, set_current_tenant_id
from app.database.connection import get_database
from app.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
)
from app.repositories.admin_repo import AdminRepository, AuditRepository, NotificationRepository
from app.repositories.attendance_repo import AttendanceRepository
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.leave_balance_repo import LeaveBalanceRepository
from app.repositories.leave_repo import HolidayRepository, LeaveRepository
from app.repositories.password_reset_repo import PasswordResetRepository
from app.repositories.regularization_repo import RegularizationRepository
from app.repositories.tenant_repo import TenantRepository
from app.security.auth import decode_access_token
from app.services.attendance_service import AttendanceService
from app.services.audit_service import AuditService
from app.services.employee_service import EmployeeService
from app.services.leave_service import HolidayService, LeaveService
from app.services.notification_service import NotificationService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


# ── Tenant Resolution Dependency ──────────────────────────────────────────────


async def get_current_tenant_id(request: Request) -> str:
    """
    Resolve tenant ID from:
    1. X-Tenant-ID HTTP header
    2. Bearer JWT token tenant_id claim
    3. Default fallback ('default')
    """
    # 1. Custom HTTP header
    header_tenant = request.headers.get("X-Tenant-ID")
    if header_tenant and header_tenant.strip():
        tenant_id = header_tenant.strip()
        set_current_tenant_id(tenant_id)
        return tenant_id

    # 2. Inspect JWT token claim if present
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header[7:].strip()
        try:
            payload = decode_access_token(raw_token)
            token_tenant = payload.get("tenant_id")
            if token_tenant and str(token_tenant).strip():
                tenant_id = str(token_tenant).strip()
                set_current_tenant_id(tenant_id)
                return tenant_id
        except Exception:
            pass

    # 3. Default fallback
    set_current_tenant_id(DEFAULT_TENANT_ID)
    return DEFAULT_TENANT_ID


# ── DB-backed repo factories ──────────────────────────────────────────────────


def get_tenant_repo(db: Any = Depends(get_database)) -> TenantRepository:
    return TenantRepository(db)


def get_employee_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> EmployeeRepository:
    return EmployeeRepository(db, tenant_id=tenant_id)


def get_attendance_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> AttendanceRepository:
    return AttendanceRepository(db, tenant_id=tenant_id)


def get_leave_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> LeaveRepository:
    return LeaveRepository(db, tenant_id=tenant_id)


def get_holiday_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> HolidayRepository:
    return HolidayRepository(db, tenant_id=tenant_id)


def get_admin_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> AdminRepository:
    return AdminRepository(db, tenant_id=tenant_id)


def get_audit_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> AuditRepository:
    return AuditRepository(db, tenant_id=tenant_id)


def get_notification_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> NotificationRepository:
    return NotificationRepository(db, tenant_id=tenant_id)


def get_regularization_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> RegularizationRepository:
    return RegularizationRepository(db, tenant_id=tenant_id)


def get_leave_balance_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> LeaveBalanceRepository:
    return LeaveBalanceRepository(db, tenant_id=tenant_id)


def get_password_reset_repo(
    db: Any = Depends(get_database),
    tenant_id: str = Depends(get_current_tenant_id),
) -> PasswordResetRepository:
    return PasswordResetRepository(db, tenant_id=tenant_id)



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
    regularization_repo: RegularizationRepository = Depends(get_regularization_repo),
    leave_repo: LeaveRepository = Depends(get_leave_repo),
) -> AttendanceService:
    from app.config import get_settings

    settings = get_settings()
    return AttendanceService(
        attendance_repo=attendance_repo,
        employee_repo=employee_repo,
        audit_service=audit_service,
        notification_service=notification_service,
        company_tz=settings.company_timezone,
        regularization_repo=regularization_repo,
        leave_repo=leave_repo,
    )


def get_leave_service(
    leave_repo: LeaveRepository = Depends(get_leave_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    audit_service: AuditService = Depends(get_audit_service),
    leave_balance_repo: LeaveBalanceRepository = Depends(get_leave_balance_repo),
) -> LeaveService:
    return LeaveService(
        leave_repo=leave_repo,
        employee_repo=employee_repo,
        audit_service=audit_service,
        leave_balance_repo=leave_balance_repo,
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
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
) -> dict[str, Any]:
    """Validate JWT and return current admin or employee document scoped to their tenant."""
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
    role = payload.get("role")
    token_tenant_id = payload.get("tenant_id") or DEFAULT_TENANT_ID

    # Ensure repos query within the token's authenticated tenant
    admin_repo.tenant_id = token_tenant_id
    employee_repo.tenant_id = token_tenant_id

    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    if role == "employee":
        emp = await employee_repo.find_by_id(admin_id)
        if emp is None or not emp.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Employee account not found or inactive.",
            )
        return {
            "admin_id": emp["employee_id"],
            "employee_id": emp["employee_id"],
            "username": emp["employee_id"],
            "name": emp["name"],
            "email": emp["email"],
            "role": "employee",
            "is_active": emp.get("is_active", True),
            "department": emp.get("department", ""),
            "tenant_id": token_tenant_id,
        }

    admin = await admin_repo.find_by_id(admin_id)
    if admin is None:
        emp = await employee_repo.find_by_id(admin_id)
        if emp is not None and emp.get("is_active", True):
            return {
                "admin_id": emp["employee_id"],
                "employee_id": emp["employee_id"],
                "username": emp["employee_id"],
                "name": emp["name"],
                "email": emp["email"],
                "role": "employee",
                "is_active": emp.get("is_active", True),
                "department": emp.get("department", ""),
                "tenant_id": token_tenant_id,
            }

    if admin is None or not admin.get("is_active"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account not found or inactive.",
        )

    admin["tenant_id"] = token_tenant_id
    return admin


async def get_optional_current_admin(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    admin_repo: AdminRepository = Depends(get_admin_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
) -> dict[str, Any] | None:
    """Validate JWT if provided, otherwise return None (allows self-service endpoints)."""
    if credentials is None:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        admin_id = payload.get("sub")
        role = payload.get("role")
        token_tenant_id = payload.get("tenant_id") or DEFAULT_TENANT_ID

        admin_repo.tenant_id = token_tenant_id
        employee_repo.tenant_id = token_tenant_id

        if not admin_id:
            return None

        if role == "employee":
            emp = await employee_repo.find_by_id(admin_id)
            if emp and emp.get("is_active", True):
                return {
                    "admin_id": emp["employee_id"],
                    "employee_id": emp["employee_id"],
                    "username": emp["employee_id"],
                    "name": emp["name"],
                    "email": emp["email"],
                    "role": "employee",
                    "is_active": emp.get("is_active", True),
                    "department": emp.get("department", ""),
                    "tenant_id": token_tenant_id,
                }

        admin = await admin_repo.find_by_id(admin_id)
        if admin:
            admin["tenant_id"] = token_tenant_id
            return admin

        emp = await employee_repo.find_by_id(admin_id)
        if emp and emp.get("is_active", True):
            return {
                "admin_id": emp["employee_id"],
                "employee_id": emp["employee_id"],
                "username": emp["employee_id"],
                "name": emp["name"],
                "email": emp["email"],
                "role": "employee",
                "is_active": emp.get("is_active", True),
                "department": emp.get("department", ""),
                "tenant_id": token_tenant_id,
            }

        return None
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
