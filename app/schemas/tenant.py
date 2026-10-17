"""Pydantic schemas for Tenant management and configuration."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field


class TenantPolicySettings(BaseModel):
    """Customizable attendance and work policies per tenant."""

    model_config = ConfigDict(populate_by_name=True)

    company_timezone: str = Field(
        default="Asia/Kolkata",
        validation_alias=AliasChoices("company_timezone", "timezone"),
    )
    min_days_per_week: int = Field(default=3, ge=1, le=7)
    min_hours_per_week: float = Field(default=15.0, ge=0.0)
    min_avg_hours_per_day: float = Field(
        default=5.0,
        ge=0.0,
        validation_alias=AliasChoices("min_avg_hours_per_day", "daily_min_average_hours"),
    )
    working_days_per_week: int = Field(default=5, ge=1, le=7)
    week_start_day: int = Field(default=0, ge=0, le=6)  # 0=Monday
    shift_start_time: str = "09:30"
    shift_end_time: str = "18:30"
    late_grace_minutes: int = Field(default=15, ge=0)
    standard_shift_hours: float = Field(default=8.0, ge=1.0)


class TenantCreateRequest(BaseModel):
    """Schema to onboard a new tenant organization."""

    tenant_id: str = Field(
        ...,
        min_length=2,
        max_length=50,
        pattern=r"^[a-z0-9_-]+$",
        description="Unique URL-friendly tenant identifier (e.g. acme-corp)",
    )
    name: str = Field(..., min_length=2, max_length=100, description="Organization display name")
    contact_email: EmailStr = Field(..., description="Primary tenant admin/contact email")
    admin_username: str | None = Field(None, min_length=3, max_length=50)
    admin_password: str | None = Field(None, min_length=6, max_length=128)
    settings: TenantPolicySettings = Field(default_factory=TenantPolicySettings)


class TenantUpdateRequest(BaseModel):
    """Schema to update an existing tenant's configuration or metadata."""

    name: str | None = Field(None, min_length=2, max_length=100)
    contact_email: EmailStr | None = None
    status: Literal["active", "suspended", "archived"] | None = None
    settings: TenantPolicySettings | None = None


class TenantResponse(BaseModel):
    """Public tenant details response."""

    model_config = ConfigDict(populate_by_name=True)

    tenant_id: str
    name: str
    contact_email: str
    status: str = "active"
    settings: TenantPolicySettings
    created_at: datetime
    updated_at: datetime
