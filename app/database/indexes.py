"""MongoDB index initialization — idempotent and safe to run on every startup with multi-tenancy."""

from __future__ import annotations

import logging
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

logger = logging.getLogger(__name__)


async def create_indexes(db: Any) -> None:
    """Create all required indexes with multi-tenant keys. Safe to call multiple times."""
    logger.info("Initializing multi-tenant MongoDB indexes…")

    await _create_tenants_indexes(db)
    await _create_employees_indexes(db)
    await _create_attendance_indexes(db)
    await _create_leave_indexes(db)
    await _create_holidays_indexes(db)
    await _create_notification_indexes(db)
    await _create_audit_indexes(db)
    await _create_admin_indexes(db)
    await _create_regularization_indexes(db)
    await _create_leave_balance_indexes(db)
    await _create_password_reset_indexes(db)

    logger.info("Multi-tenant index initialization complete.")


async def _create_tenants_indexes(db: Any) -> None:
    collection = db.tenants
    indexes = [
        IndexModel([("tenant_id", ASCENDING)], unique=True, name="uq_tenant_id"),
        IndexModel([("status", ASCENDING)], name="idx_tenant_status"),
        IndexModel([("contact_email", ASCENDING)], name="idx_tenant_contact_email"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("tenants indexes created.")


async def _create_employees_indexes(db: Any) -> None:
    collection = db.employees
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING)],
            unique=True,
            name="uq_tenant_employee_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("email", ASCENDING)],
            unique=True,
            name="uq_tenant_employee_email",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("department", ASCENDING)],
            name="idx_tenant_emp_dept",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("is_active", ASCENDING)],
            name="idx_tenant_emp_active",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("name", ASCENDING)],
            name="idx_tenant_emp_name",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("employees indexes created.")


async def _create_attendance_indexes(db: Any) -> None:
    collection = db.attendance
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("attendance_id", ASCENDING)],
            unique=True,
            name="uq_tenant_attendance_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING), ("date", ASCENDING)],
            name="idx_tenant_att_emp_date",
        ),
        IndexModel(
            [
                ("tenant_id", ASCENDING),
                ("employee_id", ASCENDING),
                ("date", ASCENDING),
                ("entry_time", ASCENDING),
            ],
            name="idx_tenant_att_emp_date_entry",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("attendance_status", ASCENDING)],
            name="idx_tenant_att_status",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("date", ASCENDING)],
            name="idx_tenant_att_date",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING)],
            name="idx_tenant_att_emp",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("attendance indexes created.")


async def _create_leave_indexes(db: Any) -> None:
    collection = db.leave_requests
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("leave_id", ASCENDING)],
            unique=True,
            name="uq_tenant_leave_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING)],
            name="idx_tenant_leave_employee",
        ),
        IndexModel(
            [
                ("tenant_id", ASCENDING),
                ("employee_id", ASCENDING),
                ("start_date", ASCENDING),
                ("end_date", ASCENDING),
            ],
            name="idx_tenant_leave_emp_dates",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("status", ASCENDING)],
            name="idx_tenant_leave_status",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("start_date", ASCENDING)],
            name="idx_tenant_leave_start",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("leave_requests indexes created.")


async def _create_holidays_indexes(db: Any) -> None:
    collection = db.holidays
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("holiday_id", ASCENDING)],
            unique=True,
            name="uq_tenant_holiday_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("date", ASCENDING)],
            unique=True,
            name="uq_tenant_holiday_date",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("name", ASCENDING)],
            name="idx_tenant_holiday_name",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("holidays indexes created.")


async def _create_notification_indexes(db: Any) -> None:
    collection = db.notification_logs
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("notification_id", ASCENDING)],
            unique=True,
            name="uq_tenant_notif_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("dedup_key", ASCENDING)],
            unique=True,
            name="uq_tenant_notif_dedup",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("status", ASCENDING)],
            name="idx_tenant_notif_status",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("next_retry_at", ASCENDING)],
            name="idx_tenant_notif_retry",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING)],
            name="idx_tenant_notif_employee",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("notification_logs indexes created.")


async def _create_audit_indexes(db: Any) -> None:
    collection = db.audit_logs
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("audit_id", ASCENDING)],
            unique=True,
            name="uq_tenant_audit_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("timestamp", DESCENDING)],
            name="idx_tenant_audit_timestamp",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("actor_id", ASCENDING)],
            name="idx_tenant_audit_actor",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("resource_type", ASCENDING)],
            name="idx_tenant_audit_res_type",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("resource_id", ASCENDING)],
            name="idx_tenant_audit_res_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING)],
            name="idx_tenant_audit_employee",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("audit_logs indexes created.")


async def _create_admin_indexes(db: Any) -> None:
    collection = db.admin_users
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("admin_id", ASCENDING)],
            unique=True,
            name="uq_tenant_admin_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("username", ASCENDING)],
            unique=True,
            name="uq_tenant_admin_username",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("email", ASCENDING)],
            unique=True,
            name="uq_tenant_admin_email",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("is_active", ASCENDING)],
            name="idx_tenant_admin_active",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("admin_users indexes created.")


async def _create_regularization_indexes(db: Any) -> None:
    collection = db.regularization_requests
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("request_id", ASCENDING)],
            unique=True,
            name="uq_tenant_reg_id",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING), ("date", ASCENDING)],
            name="idx_tenant_reg_emp_date",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("status", ASCENDING)],
            name="idx_tenant_reg_status",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_tenant_reg_created",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("regularization_requests indexes created.")


async def _create_leave_balance_indexes(db: Any) -> None:
    collection = db.leave_balances
    indexes = [
        IndexModel(
            [
                ("tenant_id", ASCENDING),
                ("employee_id", ASCENDING),
                ("year", ASCENDING),
                ("leave_type", ASCENDING),
            ],
            unique=True,
            name="uq_tenant_leave_bal_emp_yr_type",
        ),
        IndexModel(
            [("tenant_id", ASCENDING), ("employee_id", ASCENDING)],
            name="idx_tenant_leave_bal_emp",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("leave_balances indexes created.")


async def _create_password_reset_indexes(db: Any) -> None:
    collection = db.password_reset_tokens
    indexes = [
        IndexModel(
            [("tenant_id", ASCENDING), ("email", ASCENDING), ("code", ASCENDING)],
            name="idx_tenant_pwd_reset_lookup",
        ),
        IndexModel(
            [("expires_at", ASCENDING)],
            expireAfterSeconds=0,
            name="idx_pwd_reset_ttl",
        ),
    ]
    await collection.create_indexes(indexes)
    logger.debug("password_reset_tokens indexes created.")

