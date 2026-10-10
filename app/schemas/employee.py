"""Employee request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import EmailStr, Field, field_validator

from app.schemas.common import CAMSBaseModel


def _normalize_employee_id(v: str) -> str:
    return v.strip().upper()


def _normalize_email(v: str) -> str:
    return v.strip().lower()


class EmployeeCreate(CAMSBaseModel):
    employee_id: Annotated[str, Field(min_length=1, max_length=50)] | None = None
    name: Annotated[str, Field(min_length=1, max_length=200)]
    email: EmailStr
    department: Annotated[str, Field(min_length=1, max_length=100)]
    role: Annotated[str, Field(min_length=1, max_length=100)] = "Employee"

    @field_validator("employee_id")
    @classmethod
    def normalize_id(cls, v: str | None) -> str | None:
        if v is not None and v.strip() and v.strip().lower() != "string":
            return _normalize_employee_id(v)
        return None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return _normalize_email(v)


class EmployeeUpdate(CAMSBaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200)] | None = None
    email: EmailStr | None = None
    department: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    role: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    is_active: bool | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _normalize_email(v)


class EmployeeResponse(CAMSBaseModel):
    employee_id: str
    name: str
    email: str
    department: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class EmployeeListParams(CAMSBaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    department: str | None = None
    is_active: bool | None = None
    search: str | None = None  # matches name, email, employee_id
