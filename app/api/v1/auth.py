"""Authentication routes with multi-tenant support."""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import (
    get_admin_repo,
    get_current_admin,
    get_employee_repo,
    get_password_reset_repo,
    get_tenant_repo,
)
from app.config import get_settings
from app.repositories.admin_repo import AdminRepository
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.password_reset_repo import PasswordResetRepository
from app.repositories.tenant_repo import TenantRepository
from app.schemas.auth import (
    AdminRegisterRequest,
    AdminResponse,
    EmployeeRegisterRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    ResetPasswordRequest,
    ResetPasswordResponse,
    TokenResponse,
    VerifyResetCodeRequest,
)
from app.security.auth import create_access_token
from app.security.password import hash_password, verify_password
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="User login (Admin or Employee)",
    description="Authenticate with admin username or employee ID / email and password.",
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginRequest,
    admin_repo: AdminRepository = Depends(get_admin_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
) -> dict[str, Any]:
    username_clean = data.username.strip()
    active_tenant_id = data.tenant_id or admin_repo.tenant_id

    # If login request passed an explicit tenant_id different from dependency
    if data.tenant_id and data.tenant_id != admin_repo.tenant_id:
        admin_repo.tenant_id = data.tenant_id
        employee_repo.tenant_id = data.tenant_id
        active_tenant_id = data.tenant_id

    # 1. Try Administrator account (by username, email, or global super admin)
    admin = await admin_repo.find_by_username(username_clean)
    if admin is None:
        admin = await admin_repo.find_by_email(username_clean.lower())
    if admin is None:
        # Check if user is platform Super Admin across any tenant
        admin = await admin_repo.find_super_admin(username_clean)

    if admin is not None:
        if not verify_password(data.password, admin["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        if not admin.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is inactive.",
            )

        token_tenant = admin.get("tenant_id") or active_tenant_id
        token, expires_in = create_access_token(
            {
                "sub": admin["admin_id"],
                "role": admin["role"],
                "username": admin["username"],
                "name": admin.get("name") or admin["username"],
                "email": admin.get("email"),
                "tenant_id": token_tenant,
            }
        )
        logger.info(
            "%s '%s' logged in (tenant: %s).",
            admin["role"].title(),
            admin["username"],
            token_tenant,
        )
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "tenant_id": token_tenant,
        }

    # 2. Try Employee account (by ID or Email)
    emp = None
    try:
        emp = await employee_repo.find_by_id(username_clean.upper())
        if emp is None:
            emp = await employee_repo.find_by_email(username_clean.lower())
    except TypeError:
        emp = None

    if emp is not None:
        if not emp.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Employee account is inactive.",
            )

        hashed_pwd = emp.get("hashed_password")
        if not hashed_pwd:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account has no password set. Please register or create your password.",
            )

        if not verify_password(data.password, hashed_pwd):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        token, expires_in = create_access_token(
            {
                "sub": emp["employee_id"],
                "role": "employee",
                "username": emp["employee_id"],
                "employee_id": emp["employee_id"],
                "name": emp["name"],
                "email": emp["email"],
                "tenant_id": emp.get("tenant_id") or active_tenant_id,
            }
        )
        logger.info("Employee '%s' logged in (tenant: %s).", emp["employee_id"], active_tenant_id)
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": expires_in,
            "tenant_id": active_tenant_id,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password.",
    )


@router.post(
    "/register/admin",
    response_model=TokenResponse,
    summary="Register new administrator account",
    description="Create a new administrator with chosen credentials and password.",
    status_code=status.HTTP_201_CREATED,
)
async def register_admin(
    data: AdminRegisterRequest,
    admin_repo: AdminRepository = Depends(get_admin_repo),
    tenant_repo: TenantRepository = Depends(get_tenant_repo),
) -> dict[str, Any]:
    username_clean = data.username.strip()
    active_tenant_id = data.tenant_id or admin_repo.tenant_id
    if data.tenant_id and data.tenant_id != admin_repo.tenant_id:
        admin_repo.tenant_id = data.tenant_id

    # Verify that the target tenant exists (only Super Admin can onboard new tenants)
    if active_tenant_id != "default":
        tenant = await tenant_repo.find_by_id(active_tenant_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Organization '{active_tenant_id}' does not exist. "
                    "Only Super Admin can onboard new organizations."
                ),
            )

    # Protect super admin username
    if username_clean.lower() == "vishrutha":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username 'vishrutha' is reserved for platform Super Admin.",
        )

    existing_user = await admin_repo.find_by_username(username_clean)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Administrator username '{username_clean}' is already taken for this tenant.",
        )

    email_clean = data.email.lower().strip()
    if email_clean == "vishrutha7104@gmail.com":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is reserved for platform Super Admin.",
        )

    existing_email = await admin_repo.find_by_email(email_clean)
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Administrator email '{data.email}' is already registered for this tenant.",
        )

    now = datetime.now(tz=UTC)
    admin_id = f"ADM-{uuid.uuid4().hex[:8].upper()}"
    doc = {
        "admin_id": admin_id,
        "username": username_clean,
        "email": email_clean,
        "name": data.name.strip() if data.name else username_clean,
        "hashed_password": hash_password(data.password),
        "role": "admin",
        "is_active": True,
        "tenant_id": active_tenant_id,
        "created_at": now,
        "updated_at": now,
    }
    await admin_repo.create(doc)
    logger.info("New admin '%s' registered for tenant '%s'.", username_clean, active_tenant_id)

    token, expires_in = create_access_token(
        {
            "sub": admin_id,
            "role": "admin",
            "username": username_clean,
            "tenant_id": active_tenant_id,
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "tenant_id": active_tenant_id,
    }


@router.post(
    "/register/employee",
    response_model=TokenResponse,
    summary="Register new employee account",
    description="Create or activate an employee account with chosen credentials and password.",
    status_code=status.HTTP_201_CREATED,
)
async def register_employee(
    data: EmployeeRegisterRequest,
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
) -> dict[str, Any]:
    active_tenant_id = data.tenant_id or employee_repo.tenant_id
    if data.tenant_id and data.tenant_id != employee_repo.tenant_id:
        employee_repo.tenant_id = data.tenant_id

    emp_id = data.employee_id.strip().upper() if data.employee_id else None
    if not emp_id or emp_id == "STRING":
        emp_id = await employee_repo.next_employee_id()

    now = datetime.now(tz=UTC)
    email_clean = data.email.lower().strip()

    existing_emp = await employee_repo.find_by_id(emp_id)
    if existing_emp is not None:
        if existing_emp.get("hashed_password"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Employee ID '{emp_id}' is already registered with a password.",
            )
        # Account was onboarded by HR without a password: activate with their created password
        await employee_repo.update(
            emp_id,
            {
                "name": data.name.strip(),
                "department": data.department.strip(),
                "email": email_clean,
                "hashed_password": hash_password(data.password),
                "updated_at": now,
            },
        )
        logger.info("Employee '%s' activated with their chosen password.", emp_id)
    else:
        existing_by_email = await employee_repo.find_by_email(email_clean)
        if existing_by_email is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Email '{email_clean}' is already registered "
                    "for another employee in this tenant."
                ),
            )

        doc = {
            "employee_id": emp_id,
            "name": data.name.strip(),
            "email": email_clean,
            "department": data.department.strip(),
            "role": "Employee",
            "is_active": True,
            "tenant_id": active_tenant_id,
            "hashed_password": hash_password(data.password),
            "created_at": now,
            "updated_at": now,
        }
        await employee_repo.create(doc)
        logger.info("New employee '%s' registered for tenant '%s'.", emp_id, active_tenant_id)

    token, expires_in = create_access_token(
        {
            "sub": emp_id,
            "role": "employee",
            "username": emp_id,
            "employee_id": emp_id,
            "name": data.name.strip(),
            "email": email_clean,
            "tenant_id": active_tenant_id,
        }
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "tenant_id": active_tenant_id,
    }


@router.get(
    "/me",
    response_model=AdminResponse,
    summary="Get current admin profile",
    description="Returns the authenticated administrator's profile.",
)
async def get_me(
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    # Remove sensitive fields before returning
    safe = {k: v for k, v in current_admin.items() if k != "hashed_password"}
    return safe


@router.post(
    "/forgot-password",
    response_model=ForgotPasswordResponse,
    summary="Request password reset verification code",
    description="Sends an email with a 6-digit verification code to reset account password.",
    status_code=status.HTTP_200_OK,
)
async def forgot_password(
    data: ForgotPasswordRequest,
    admin_repo: AdminRepository = Depends(get_admin_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    reset_repo: PasswordResetRepository = Depends(get_password_reset_repo),
) -> dict[str, Any]:
    active_tenant_id = data.tenant_id or admin_repo.tenant_id
    if data.tenant_id and data.tenant_id != admin_repo.tenant_id:
        admin_repo.tenant_id = data.tenant_id
        employee_repo.tenant_id = data.tenant_id
        reset_repo.tenant_id = data.tenant_id

    email_clean = data.email.lower().strip()

    # Search in admin accounts first
    user_id = None
    user_type = None
    user_name = "User"

    admin = await admin_repo.find_by_email(email_clean)
    if admin is not None:
        user_id = admin["admin_id"]
        user_type = "admin"
        user_name = admin.get("name") or admin["username"]
    else:
        # Search in employee accounts
        emp = await employee_repo.find_by_email(email_clean)
        if emp is not None:
            user_id = emp["employee_id"]
            user_type = "employee"
            user_name = emp.get("name") or emp["employee_id"]

    if not user_id or not user_type:
        # For security, return generic success message to prevent user enumeration
        return {
            "message": "If an account exists with that email, a verification code has been sent.",
            "tenant_id": active_tenant_id,
        }

    # Generate 6-digit numeric verification code
    code = f"{secrets.randbelow(900000) + 100000}"
    await reset_repo.create_reset_token(
        user_id=user_id,
        user_type=user_type,
        email=email_clean,
        code=code,
        expires_in_minutes=15,
    )

    # Send verification email
    notification_svc = NotificationService()
    await notification_svc.send_password_reset_email(
        to_email=email_clean,
        user_name=user_name,
        reset_code=code,
        tenant_id=active_tenant_id,
    )

    settings = get_settings()
    dev_code = code if settings.app_env != "production" else None

    logger.info(
        "Password reset initiated for %s [%s] in tenant '%s'.",
        email_clean,
        user_type,
        active_tenant_id,
    )
    return {
        "message": f"Verification code sent to {email_clean}.",
        "tenant_id": active_tenant_id,
        "dev_code": dev_code,
    }


@router.post(
    "/verify-reset-code",
    summary="Verify reset code",
    description="Validates that a password reset code is valid and unexpired.",
    status_code=status.HTTP_200_OK,
)
async def verify_reset_code(
    data: VerifyResetCodeRequest,
    reset_repo: PasswordResetRepository = Depends(get_password_reset_repo),
) -> dict[str, Any]:
    active_tenant_id = data.tenant_id or reset_repo.tenant_id
    if data.tenant_id and data.tenant_id != reset_repo.tenant_id:
        reset_repo.tenant_id = data.tenant_id

    token = await reset_repo.find_valid_token(data.email, data.code)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    return {
        "valid": True,
        "message": "Verification code is valid.",
        "tenant_id": active_tenant_id,
    }


@router.post(
    "/reset-password",
    response_model=ResetPasswordResponse,
    summary="Change password using verified reset code",
    description="Updates account password using a valid email verification code.",
    status_code=status.HTTP_200_OK,
)
async def reset_password(
    data: ResetPasswordRequest,
    admin_repo: AdminRepository = Depends(get_admin_repo),
    employee_repo: EmployeeRepository = Depends(get_employee_repo),
    reset_repo: PasswordResetRepository = Depends(get_password_reset_repo),
) -> dict[str, Any]:
    active_tenant_id = data.tenant_id or reset_repo.tenant_id
    if data.tenant_id and data.tenant_id != reset_repo.tenant_id:
        admin_repo.tenant_id = data.tenant_id
        employee_repo.tenant_id = data.tenant_id
        reset_repo.tenant_id = data.tenant_id

    token = await reset_repo.find_valid_token(data.email, data.code)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification code.",
        )

    new_hash = hash_password(data.new_password)
    email_clean = data.email.lower().strip()
    user_type = token.get("user_type")
    user_id = token.get("user_id")

    if user_type == "admin":
        updated = await admin_repo.update_password(email_clean, new_hash)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Admin account not found.",
            )
    else:
        # employee
        if not user_id:
            emp = await employee_repo.find_by_email(email_clean)
            user_id = emp["employee_id"] if emp else None

        if user_id:
            await employee_repo.update(user_id, {"hashed_password": new_hash})
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Employee account not found.",
            )

    # Invalidate token
    await reset_repo.mark_used(email_clean, data.code)
    logger.info(
        "Password successfully reset for %s [%s] in tenant '%s'.",
        email_clean,
        user_type,
        active_tenant_id,
    )
    return {
        "message": "Password successfully reset. You may now sign in.",
        "tenant_id": active_tenant_id,
    }
