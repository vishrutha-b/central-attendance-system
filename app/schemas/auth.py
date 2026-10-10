"""Authentication schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import CAMSBaseModel

AdminRole = Literal["super_admin", "admin", "manager", "employee"]


class LoginRequest(CAMSBaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(CAMSBaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class AdminResponse(CAMSBaseModel):
    admin_id: str
    username: str
    email: str
    role: AdminRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminCreate(CAMSBaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    password: str = Field(min_length=8)
    role: AdminRole = "admin"
