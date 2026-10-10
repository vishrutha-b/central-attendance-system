"""Attendance service — session management and validation."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from app.exceptions import (
    AttendanceSequenceError,
    EmployeeInactiveError,
)
from app.repositories.attendance_repo import AttendanceRepository
from app.repositories.employee_repo import EmployeeRepository
from app.schemas.attendance import (
    AttendanceCorrection,
    AttendanceEntryRequest,
    AttendanceExitRequest,
    AttendanceQuickRecordRequest,
    parse_flexible_datetime,
)
from app.services.audit_service import AuditService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


def _session_to_date_str(entry_time: datetime, company_tz_name: str = "Asia/Kolkata") -> str:
    """Convert a UTC entry_time to the local date string in company timezone."""
    try:
        from zoneinfo import ZoneInfo

        local_dt = entry_time.astimezone(ZoneInfo(company_tz_name))
        return local_dt.date().isoformat()
    except Exception:
        return entry_time.date().isoformat()


def _ensure_utc(dt: datetime) -> datetime:
    """Make a datetime timezone-aware UTC. MongoDB returns naive UTC datetimes."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class AttendanceService:
    def __init__(
        self,
        attendance_repo: AttendanceRepository,
        employee_repo: EmployeeRepository,
        audit_service: AuditService,
        notification_service: NotificationService | None = None,
        company_tz: str = "Asia/Kolkata",
    ) -> None:
        self.attendance_repo = attendance_repo
        self.employee_repo = employee_repo
        self.audit_service = audit_service
        self.notification_service = notification_service or NotificationService()
        self.company_tz = company_tz

    async def record_entry(self, data: AttendanceEntryRequest, actor_id: str) -> dict[str, Any]:
        """Record a new attendance entry for an employee."""
        employee = await self.employee_repo.get_or_raise(data.employee_id)
        if not employee["is_active"]:
            raise EmployeeInactiveError(f"Employee '{data.employee_id}' is inactive.")

        # Check for an open session
        open_session = await self.attendance_repo.find_open_session(data.employee_id)
        if open_session is not None:
            raise AttendanceSequenceError(
                f"Employee '{data.employee_id}' has an open session "
                f"(attendance_id={open_session['attendance_id']}). "
                "Record exit before starting a new session."
            )

        now = datetime.now(tz=UTC)
        if isinstance(data.entry_time, datetime):
            entry_dt = data.entry_time
        elif data.entry_time:
            entry_dt = datetime.fromisoformat(str(data.entry_time))
        else:
            entry_dt = now

        # Resolve the attendance date: explicit date field wins, else derive from entry_time
        if data.date is not None:
            if isinstance(data.date, str):
                attendance_date = data.date.strip()
            else:
                attendance_date = data.date.isoformat()
        else:
            attendance_date = _session_to_date_str(entry_dt, self.company_tz)
        attendance_id = f"ATT-{uuid.uuid4().hex[:12].upper()}"

        doc = {
            "attendance_id": attendance_id,
            "employee_id": data.employee_id,
            "date": attendance_date,
            "entry_time": entry_dt,
            "exit_time": None,
            "total_hours": 0.0,
            "attendance_status": "incomplete",
            "created_at": now,
            "updated_at": now,
        }
        created = await self.attendance_repo.create(doc)
        logger.info("Entry recorded: %s for %s", attendance_id, data.employee_id)

        await self.audit_service.log(
            actor_id=actor_id,
            action="attendance.entry",
            resource_type="attendance",
            resource_id=attendance_id,
            employee_id=data.employee_id,
            new_values={"entry_time": entry_dt.isoformat(), "date": attendance_date},
        )
        return created

    async def record_exit(self, data: AttendanceExitRequest, actor_id: str) -> dict[str, Any]:
        """Record exit for the employee's current open session."""
        employee = await self.employee_repo.get_or_raise(data.employee_id)
        if not employee["is_active"]:
            raise EmployeeInactiveError(f"Employee '{data.employee_id}' is inactive.")

        open_session = await self.attendance_repo.find_open_session(data.employee_id)
        if open_session is None:
            raise AttendanceSequenceError(
                f"No open attendance session found for employee '{data.employee_id}'. "
                "Record entry before exit."
            )

        entry_time: datetime = _ensure_utc(open_session["entry_time"])
        exit_time: datetime = _ensure_utc(data.exit_time)  # type: ignore[arg-type]

        # If data.date was not explicitly specified, align exit_time date with open_session date
        if data.date is None and open_session.get("date"):
            s_date_raw = open_session["date"]
            s_date = date.fromisoformat(s_date_raw) if isinstance(s_date_raw, str) else s_date_raw
            if exit_time.date() != s_date:
                from zoneinfo import ZoneInfo

                tz = ZoneInfo(self.company_tz)
                local_exit = exit_time.astimezone(tz)
                aligned_local = local_exit.replace(
                    year=s_date.year,
                    month=s_date.month,
                    day=s_date.day,
                )
                exit_time = _ensure_utc(aligned_local)

        if exit_time <= entry_time:
            raise AttendanceSequenceError(
                f"Exit time ({exit_time.isoformat()}) must be after "
                f"entry time ({entry_time.isoformat()})."
            )

        delta_seconds = (exit_time - entry_time).total_seconds()
        total_hours = round(delta_seconds / 3600.0, 4)

        updated = await self.attendance_repo.update(
            open_session["attendance_id"],
            {
                "exit_time": exit_time,
                "total_hours": total_hours,
                "attendance_status": "complete",
            },
        )
        logger.info(
            "Exit recorded: %s for %s (%.2f hrs)",
            open_session["attendance_id"],
            data.employee_id,
            total_hours,
        )

        # Check daily working hours policy (< 5 hrs triggers automatic alert email)
        from app.config import get_settings

        settings = get_settings()
        min_daily = settings.min_avg_hours_per_day

        session_date = open_session.get("date") or _session_to_date_str(entry_time, self.company_tz)
        if isinstance(session_date, str):
            date_obj = date.fromisoformat(session_date)
        elif isinstance(session_date, date):
            date_obj = session_date
        else:
            date_obj = entry_time.date()
        date_str = date_obj.isoformat()

        try:
            day_sessions = await self.attendance_repo.find_sessions_for_date(
                data.employee_id, date_obj
            )
            day_total_hours = sum(s.get("total_hours", 0.0) for s in day_sessions)
        except Exception:
            day_total_hours = total_hours

        if day_total_hours < min_daily:
            alert_msg = (
                f"Policy non-compliance: {day_total_hours:.2f} hrs is less than mandatory "
                f"{min_daily:.1f} hrs/day. Automated alert email dispatched to {employee['email']}."
            )
            updated["policy_alert"] = alert_msg
            try:
                await self.notification_service.send_daily_violation_email(
                    employee_email=employee["email"],
                    employee_name=employee["name"],
                    employee_id=employee["employee_id"],
                    department=employee.get("department", "General"),
                    attendance_date=date_str,
                    hours_worked=day_total_hours,
                    min_required_hours=min_daily,
                    entry_time_str=entry_time.strftime("%I:%M %p"),
                    exit_time_str=exit_time.strftime("%I:%M %p"),
                )
            except Exception as e:
                logger.error("Failed to send daily violation email: %s", e)

        await self.audit_service.log(
            actor_id=actor_id,
            action="attendance.exit",
            resource_type="attendance",
            resource_id=open_session["attendance_id"],
            employee_id=data.employee_id,
            new_values={
                "exit_time": exit_time.isoformat(),
                "total_hours": total_hours,
            },
        )
        return updated

    async def correct_attendance(
        self,
        attendance_id: str,
        data: AttendanceCorrection,
        actor_id: str,
    ) -> dict[str, Any]:
        """Correct an attendance record. Requires admin authorization (enforced at route)."""
        existing = await self.attendance_repo.get_or_raise(attendance_id)

        # Normalize existing datetimes from MongoDB (may be naive UTC)
        existing_entry = _ensure_utc(existing["entry_time"]) if existing.get("entry_time") else None
        existing_exit = _ensure_utc(existing["exit_time"]) if existing.get("exit_time") else None

        old_values = {
            "entry_time": existing_entry.isoformat() if existing_entry else None,
            "exit_time": existing_exit.isoformat() if existing_exit else None,
        }

        updates: dict[str, Any] = {}
        entry_time = data.entry_time or existing_entry
        exit_time = data.exit_time or existing_exit

        if data.entry_time is not None:
            updates["entry_time"] = data.entry_time
        if data.exit_time is not None:
            updates["exit_time"] = data.exit_time

        # Recalculate hours if both times are present
        if entry_time and exit_time:
            entry_time = _ensure_utc(entry_time)  # type: ignore[arg-type]
            exit_time = _ensure_utc(exit_time)  # type: ignore[arg-type]
            if exit_time <= entry_time:
                raise AttendanceSequenceError("exit_time must be after entry_time.")
            delta = (exit_time - entry_time).total_seconds()
            updates["total_hours"] = round(delta / 3600.0, 4)
            updates["attendance_status"] = "complete"
        elif entry_time and not exit_time:
            updates["total_hours"] = 0.0
            updates["attendance_status"] = "incomplete"

        updated = await self.attendance_repo.update(attendance_id, updates)
        logger.info("Attendance corrected: %s by actor %s", attendance_id, actor_id)

        await self.audit_service.log(
            actor_id=actor_id,
            action="attendance.correction",
            resource_type="attendance",
            resource_id=attendance_id,
            employee_id=existing["employee_id"],
            previous_values=old_values,
            new_values={k: str(v) for k, v in updates.items() if k != "updated_at"},
            outcome="corrected",
        )
        return updated

    async def get_attendance_for_date(
        self, employee_id: str, attendance_date: str
    ) -> list[dict[str, Any]]:
        d = date.fromisoformat(attendance_date)
        return await self.attendance_repo.find_sessions_for_date(employee_id.upper(), d)

    async def quick_record(
        self, data: AttendanceQuickRecordRequest, actor_id: str
    ) -> dict[str, Any]:
        """Record a complete attendance session (entry + exit) in a single call."""
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(self.company_tz)

        # Resolve attendance date
        if data.date is None:
            attendance_date_obj = datetime.now(tz=tz).date()
        elif isinstance(data.date, str):
            attendance_date_obj = date.fromisoformat(data.date.strip())
        else:
            attendance_date_obj = data.date

        # Resolve entry time — default to 09:00 on the attendance date
        entry_time = parse_flexible_datetime(
            data.entry_time if data.entry_time is not None else "09:00",
            default_to_now=False,
            base_date=attendance_date_obj,
            company_tz_name=self.company_tz,
        )

        # Resolve exit time — default to 18:00 on the attendance date
        exit_time = parse_flexible_datetime(
            data.exit_time if data.exit_time is not None else "18:00",
            default_to_now=False,
            base_date=attendance_date_obj,
            company_tz_name=self.company_tz,
        )

        if entry_time is None or exit_time is None:
            raise AttendanceSequenceError("entry_time and exit_time are required for quick-record.")

        if exit_time <= entry_time:
            raise AttendanceSequenceError("exit_time must be after entry_time.")

        employee = await self.employee_repo.get_or_raise(data.employee_id)
        if not employee["is_active"]:
            raise EmployeeInactiveError(f"Employee '{data.employee_id}' is inactive.")

        delta_seconds = (exit_time - entry_time).total_seconds()
        total_hours = round(delta_seconds / 3600.0, 4)
        now = datetime.now(tz=UTC)
        attendance_id = f"ATT-{uuid.uuid4().hex[:12].upper()}"
        attendance_date_str = attendance_date_obj.isoformat()

        doc = {
            "attendance_id": attendance_id,
            "employee_id": data.employee_id,
            "date": attendance_date_str,
            "entry_time": entry_time,
            "exit_time": exit_time,
            "total_hours": total_hours,
            "attendance_status": "complete",
            "created_at": now,
            "updated_at": now,
        }
        created = await self.attendance_repo.create(doc)
        logger.info(
            "Quick record: %s for %s on %s (%.2f hrs)",
            attendance_id,
            data.employee_id,
            attendance_date_str,
            total_hours,
        )

        # Check daily working hours policy (< 5 hrs triggers automatic alert email)
        from app.config import get_settings

        settings = get_settings()
        min_daily = settings.min_avg_hours_per_day

        try:
            day_sessions = await self.attendance_repo.find_sessions_for_date(
                data.employee_id, attendance_date_obj
            )
            day_total_hours = sum(s.get("total_hours", 0.0) for s in day_sessions)
        except Exception:
            day_total_hours = total_hours

        if day_total_hours < min_daily:
            alert_msg = (
                f"Policy non-compliance: {day_total_hours:.2f} hrs is less than mandatory "
                f"{min_daily:.1f} hrs/day. Automated alert email dispatched to {employee['email']}."
            )
            created["policy_alert"] = alert_msg
            try:
                await self.notification_service.send_daily_violation_email(
                    employee_email=employee["email"],
                    employee_name=employee["name"],
                    employee_id=employee["employee_id"],
                    department=employee.get("department", "General"),
                    attendance_date=attendance_date_str,
                    hours_worked=day_total_hours,
                    min_required_hours=min_daily,
                    entry_time_str=entry_time.strftime("%I:%M %p"),
                    exit_time_str=exit_time.strftime("%I:%M %p"),
                )
            except Exception as e:
                logger.error("Failed to send daily violation email: %s", e)

        await self.audit_service.log(
            actor_id=actor_id,
            action="attendance.quick_record",
            resource_type="attendance",
            resource_id=attendance_id,
            employee_id=data.employee_id,
            new_values={
                "date": attendance_date_str,
                "entry_time": entry_time.isoformat(),
                "exit_time": exit_time.isoformat(),
                "total_hours": total_hours,
            },
        )
        return created

    async def get_attendance_history(
        self,
        employee_id: str,
        page: int = 1,
        page_size: int = 20,
        start_date: Any = None,
        end_date: Any = None,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * page_size
        return await self.attendance_repo.list_for_employee(
            employee_id=employee_id.upper(),
            skip=skip,
            limit=page_size,
            start_date=start_date,
            end_date=end_date,
        )
