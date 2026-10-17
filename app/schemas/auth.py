"""Authentication schemas with multi-tenant support."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field

from app.schemas.common import CAMSBaseModel

AdminRole = Literal["super_admin", "admin", "manager", "employee"]


class LoginRequest(CAMSBaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    tenant_id: str | None = Field(default=None, description="Optional tenant identifier")


class TokenResponse(CAMSBaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    tenant_id: str = "default"


class AdminResponse(CAMSBaseModel):
    admin_id: str
    username: str
    email: str
    role: AdminRole
    is_active: bool
    tenant_id: str | None = "default"
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
    tenant_id: str | None = None


class AdminRegisterRequest(CAMSBaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=150)
    password: str = Field(min_length=6, max_length=128)
    name: str | None = None
    tenant_id: str | None = None


class EmployeeRegisterRequest(CAMSBaseModel):
    employee_id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=5, max_length=150)
    department: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=6, max_length=128)
    tenant_id: str | None = None


class ForgotPasswordRequest(CAMSBaseModel):
    email: str = Field(min_length=3, max_length=150)
    tenant_id: str | None = None


class ForgotPasswordResponse(CAMSBaseModel):
    message: str
    tenant_id: str
    dev_code: str | None = None


class VerifyResetCodeRequest(CAMSBaseModel):
    email: str = Field(min_length=3, max_length=150)
    code: str = Field(min_length=4, max_length=20)
    tenant_id: str | None = None


class ResetPasswordRequest(CAMSBaseModel):
    email: str = Field(min_length=3, max_length=150)
    code: str = Field(min_length=4, max_length=20)
    new_password: str = Field(min_length=6, max_length=128)
    tenant_id: str | None = None


class ResetPasswordResponse(CAMSBaseModel):
    message: str
    tenant_id: str

