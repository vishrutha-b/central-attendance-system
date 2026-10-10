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
    name: str | None = None
    employee_id: str | None = None
    department: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminCreate(CAMSBaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str
    password: str = Field(min_length=6)
    role: AdminRole = "admin"


class AdminRegisterRequest(CAMSBaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=6, max_length=128)
    name: str | None = None


class EmployeeRegisterRequest(CAMSBaseModel):
    employee_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=5, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=128)

