"""MongoDB index initialization — idempotent and safe to run on every startup."""

from __future__ import annotations

import logging
from typing import Any

from pymongo import ASCENDING, DESCENDING, IndexModel

logger = logging.getLogger(__name__)


async def create_indexes(db: Any) -> None:
    """Create all required indexes. Safe to call multiple times."""
    logger.info("Initializing MongoDB indexes…")

    await _create_employees_indexes(db)
    await _create_attendance_indexes(db)
    await _create_leave_indexes(db)
    await _create_holidays_indexes(db)
    await _create_notification_indexes(db)
    await _create_audit_indexes(db)
    await _create_admin_indexes(db)

    logger.info("Index initialization complete.")


async def _create_employees_indexes(db: Any) -> None:
    collection = db.employees
    indexes = [
        IndexModel([("employee_id", ASCENDING)], unique=True, name="uq_employee_id"),
        IndexModel([("email", ASCENDING)], unique=True, name="uq_employee_email"),
        IndexModel([("department", ASCENDING)], name="idx_employee_department"),
        IndexModel([("is_active", ASCENDING)], name="idx_employee_active"),
        IndexModel([("name", ASCENDING)], name="idx_employee_name"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("employees indexes created.")


async def _create_attendance_indexes(db: Any) -> None:
    collection = db.attendance
    indexes = [
        IndexModel([("attendance_id", ASCENDING)], unique=True, name="uq_attendance_id"),
        IndexModel(
            [("employee_id", ASCENDING), ("date", ASCENDING)],
            name="idx_attendance_emp_date",
        ),
        IndexModel(
            [("employee_id", ASCENDING), ("date", ASCENDING), ("entry_time", ASCENDING)],
            name="idx_attendance_emp_date_entry",
        ),
        IndexModel([("attendance_status", ASCENDING)], name="idx_attendance_status"),
        IndexModel([("date", ASCENDING)], name="idx_attendance_date"),
        IndexModel([("employee_id", ASCENDING)], name="idx_attendance_employee"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("attendance indexes created.")


async def _create_leave_indexes(db: Any) -> None:
    collection = db.leave_requests
    indexes = [
        IndexModel([("leave_id", ASCENDING)], unique=True, name="uq_leave_id"),
        IndexModel([("employee_id", ASCENDING)], name="idx_leave_employee"),
        IndexModel(
            [("employee_id", ASCENDING), ("start_date", ASCENDING), ("end_date", ASCENDING)],
            name="idx_leave_emp_dates",
        ),
        IndexModel([("status", ASCENDING)], name="idx_leave_status"),
        IndexModel([("start_date", ASCENDING)], name="idx_leave_start"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("leave_requests indexes created.")


async def _create_holidays_indexes(db: Any) -> None:
    collection = db.holidays
    indexes = [
        IndexModel([("holiday_id", ASCENDING)], unique=True, name="uq_holiday_id"),
        IndexModel([("date", ASCENDING)], unique=True, name="uq_holiday_date"),
        IndexModel([("name", ASCENDING)], name="idx_holiday_name"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("holidays indexes created.")


async def _create_notification_indexes(db: Any) -> None:
    collection = db.notification_logs
    indexes = [
        IndexModel([("notification_id", ASCENDING)], unique=True, name="uq_notification_id"),
        IndexModel([("dedup_key", ASCENDING)], unique=True, name="uq_notification_dedup"),
        IndexModel([("status", ASCENDING)], name="idx_notification_status"),
        IndexModel([("next_retry_at", ASCENDING)], name="idx_notification_retry"),
        IndexModel([("employee_id", ASCENDING)], name="idx_notification_employee"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("notification_logs indexes created.")


async def _create_audit_indexes(db: Any) -> None:
    collection = db.audit_logs
    indexes = [
        IndexModel([("audit_id", ASCENDING)], unique=True, name="uq_audit_id"),
        IndexModel([("timestamp", DESCENDING)], name="idx_audit_timestamp"),
        IndexModel([("actor_id", ASCENDING)], name="idx_audit_actor"),
        IndexModel([("resource_type", ASCENDING)], name="idx_audit_resource_type"),
        IndexModel([("resource_id", ASCENDING)], name="idx_audit_resource"),
        IndexModel([("employee_id", ASCENDING)], name="idx_audit_employee"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("audit_logs indexes created.")


async def _create_admin_indexes(db: Any) -> None:
    collection = db.admin_users
    indexes = [
        IndexModel([("admin_id", ASCENDING)], unique=True, name="uq_admin_id"),
        IndexModel([("username", ASCENDING)], unique=True, name="uq_admin_username"),
        IndexModel([("email", ASCENDING)], unique=True, name="uq_admin_email"),
        IndexModel([("is_active", ASCENDING)], name="idx_admin_active"),
    ]
    await collection.create_indexes(indexes)
    logger.debug("admin_users indexes created.")
