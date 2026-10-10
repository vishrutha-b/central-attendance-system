"""Authentication routes."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_admin_repo, get_current_admin, get_employee_repo
from app.repositories.admin_repo import AdminRepository
from app.repositories.employee_repo import EmployeeRepository
from app.schemas.auth import (
    AdminRegisterRequest,
    AdminResponse,
    EmployeeRegisterRequest,
    LoginRequest,
    TokenResponse,
)
from app.security.auth import create_access_token
from app.security.password import hash_password, verify_password

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

    # 1. Try Administrator account
    admin = await admin_repo.find_by_username(username_clean)
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

        token, expires_in = create_access_token(
            {"sub": admin["admin_id"], "role": admin["role"], "username": admin["username"]}
        )
        logger.info("Admin '%s' logged in.", admin["username"])
        return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}

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
            }
        )
        logger.info("Employee '%s' logged in.", emp["employee_id"])
        return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}

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
) -> dict[str, Any]:
    username_clean = data.username.strip()
    existing_user = await admin_repo.find_by_username(username_clean)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Administrator username '{username_clean}' is already taken.",
        )

    email_clean = data.email.lower().strip()
    existing_email = await admin_repo.find_by_email(email_clean)
    if existing_email is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Administrator email '{data.email}' is already registered.",
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
        "created_at": now,
        "updated_at": now,
    }
    await admin_repo.create(doc)
    logger.info("New admin '%s' registered.", username_clean)

    token, expires_in = create_access_token(
        {"sub": admin_id, "role": "admin", "username": username_clean}
    )
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}


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
                detail=f"Email '{email_clean}' is already registered for another employee.",
            )

        doc = {
            "employee_id": emp_id,
            "name": data.name.strip(),
            "email": email_clean,
            "department": data.department.strip(),
            "role": "Employee",
            "is_active": True,
            "hashed_password": hash_password(data.password),
            "created_at": now,
            "updated_at": now,
        }
        await employee_repo.create(doc)
        logger.info("New employee '%s' registered with their chosen password.", emp_id)

    token, expires_in = create_access_token(
        {
            "sub": emp_id,
            "role": "employee",
            "username": emp_id,
            "employee_id": emp_id,
            "name": data.name.strip(),
            "email": email_clean,
        }
    )
    return {"access_token": token, "token_type": "bearer", "expires_in": expires_in}


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
