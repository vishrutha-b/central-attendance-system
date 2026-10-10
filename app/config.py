"""
Central Attendance Management System - Application Configuration

Uses pydantic-settings to load from environment variables / .env file.
Validates all required configuration at startup.
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_env: Literal["development", "production", "testing"] = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_name: str = "Central Attendance Management System"

    # ── MongoDB ───────────────────────────────────────────────────────────────
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "cams_dev"
    mongodb_test_db_name: str = "cams_test"

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret: str = Field(default="dev_secret_key_at_least_32_characters_long", min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60

    # ── Initial Admin ────────────────────────────────────────────────────────
    initial_admin_username: str = "admin"
    initial_admin_email: str = "admin@company.com"
    initial_admin_password: str = Field(default="Admin@123456", min_length=8)

    # ── Company Settings ──────────────────────────────────────────────────────
    company_timezone: str = "Asia/Kolkata"
    week_start_day: int = Field(default=0, ge=0, le=6)  # 0=Monday

    # ── Attendance Policy ─────────────────────────────────────────────────────
    min_days_per_week: int = Field(default=3, ge=1)
    min_hours_per_week: float = Field(default=15.0, ge=0.0)
    min_avg_hours_per_day: float = Field(default=5.0, ge=0.0)
    allow_multiple_sessions: bool = True

    # ── Leave & Holiday Policy ────────────────────────────────────────────────
    working_days_per_week: int = Field(default=5, ge=1, le=7)

    # ── SMTP ──────────────────────────────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_from_address: str = "noreply@company.com"
    smtp_from_name: str = "CAMS Notifications"
    smtp_timeout_seconds: int = 30

    # ── Email Delivery Mode ───────────────────────────────────────────────────
    email_delivery_mode: Literal["smtp", "console", "disabled"] = "console"

    # ── Notification Settings ─────────────────────────────────────────────────
    notification_max_retries: int = Field(default=3, ge=0)
    notification_retry_backoff_minutes: int = Field(default=30, ge=1)

    # ── Scheduler ─────────────────────────────────────────────────────────────
    scheduler_cron: str = "0 8 * * *"
    scheduler_timezone: str = "Asia/Kolkata"

    # ── Logging ───────────────────────────────────────────────────────────────
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ── Pagination ────────────────────────────────────────────────────────────
    default_page_size: int = Field(default=20, ge=1)
    max_page_size: int = Field(default=100, ge=1)

    # ── Reporting ─────────────────────────────────────────────────────────────
    max_report_date_range_days: int = Field(default=366, ge=1)

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters")
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> Settings:
        if self.app_env == "production":
            insecure_defaults = [
                "REPLACE_WITH_SECURE_RANDOM_SECRET_MIN_32_CHARS",
                "dev_secret_change_this_in_production_min_32_chars",
            ]
            if self.jwt_secret in insecure_defaults:
                raise ValueError("Production requires a secure JWT_SECRET")
            if self.initial_admin_password in ("Admin@123456", "password", "admin"):
                raise ValueError("Production requires a secure INITIAL_ADMIN_PASSWORD")
        return self


# Singleton settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
