"""Authentication routes."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_admin_repo, get_current_admin
from app.repositories.admin_repo import AdminRepository
from app.schemas.auth import AdminResponse, LoginRequest, TokenResponse
from app.security.auth import create_access_token
from app.security.password import verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Admin login",
    description="Authenticate with username and password. Returns a JWT access token.",
    status_code=status.HTTP_200_OK,
)
async def login(
    data: LoginRequest,
    admin_repo: AdminRepository = Depends(get_admin_repo),
) -> dict[str, Any]:
    admin = await admin_repo.find_by_username(data.username)

    if admin is None or not verify_password(data.password, admin["hashed_password"]):
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
