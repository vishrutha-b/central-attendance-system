"""Attendance service — session management and validation."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime
from typing import Any

from app.exceptions import (
    AttendanceSequenceError,
    EmployeeInactiveError,
    RegularizationTransitionError,
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
from app.schemas.regularization import (
    RegularizationCreate,
    RegularizationDecision,
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
        regularization_repo: Any = None,
        leave_repo: Any = None,
    ) -> None:
        self.attendance_repo = attendance_repo
        self.employee_repo = employee_repo
        self.audit_service = audit_service
        self.notification_service = notification_service or NotificationService()
        self.company_tz = company_tz
        self.regularization_repo = regularization_repo
        self.leave_repo = leave_repo

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

    async def create_regularization(
        self, data: RegularizationCreate, actor_id: str
    ) -> dict[str, Any]:
        """Submit an attendance regularization request."""
        employee = await self.employee_repo.get_or_raise(data.employee_id)
        if not employee.get("is_active", True):
            raise EmployeeInactiveError(f"Employee '{data.employee_id}' is inactive.")

        if self.regularization_repo is None:
            raise ValueError("RegularizationRepository not configured.")

        entry_dt = parse_flexible_datetime(
            data.requested_entry_time,
            base_date=data.date,
            company_tz_name=self.company_tz,
        )
        exit_dt = parse_flexible_datetime(
            data.requested_exit_time,
            base_date=data.date,
            company_tz_name=self.company_tz,
        )
        if exit_dt <= entry_dt:
            raise AttendanceSequenceError("requested_exit_time must be after requested_entry_time.")

        now = datetime.now(tz=UTC)
        req_id = f"REG-{uuid.uuid4().hex[:10].upper()}"
        doc = {
            "request_id": req_id,
            "employee_id": data.employee_id,
            "date": data.date.isoformat(),
            "requested_entry_time": entry_dt.isoformat(),
            "requested_exit_time": exit_dt.isoformat(),
            "reason": data.reason,
            "notes": data.notes,
            "status": "pending",
            "reviewed_by": None,
            "reviewer_notes": None,
            "created_at": now,
            "updated_at": now,
        }
        created = await self.regularization_repo.create(doc)
        await self.audit_service.log(
            actor_id=actor_id,
            action="regularization.create",
            resource_type="regularization",
            resource_id=req_id,
            employee_id=data.employee_id,
            new_values={
                "date": data.date.isoformat(),
                "reason": data.reason,
                "entry": entry_dt.isoformat(),
                "exit": exit_dt.isoformat(),
            },
        )
        return created

    async def list_regularizations(
        self,
        page: int = 1,
        page_size: int = 20,
        employee_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List regularization requests with optional filtering."""
        if self.regularization_repo is None:
            return [], 0
        skip = (page - 1) * page_size
        return await self.regularization_repo.list_requests(
            skip=skip, limit=page_size, employee_id=employee_id, status=status
        )

    async def review_regularization(
        self, request_id: str, decision: RegularizationDecision, reviewer_id: str
    ) -> dict[str, Any]:
        """Approve or reject an attendance regularization request."""
        if self.regularization_repo is None:
            raise ValueError("RegularizationRepository not configured.")

        req = await self.regularization_repo.get_or_raise(request_id)
        if req["status"] != "pending":
            raise RegularizationTransitionError(
                f"Cannot review regularization request in status '{req['status']}'."
            )

        if decision.action == "approved":
            entry_dt = datetime.fromisoformat(req["requested_entry_time"])
            exit_dt = datetime.fromisoformat(req["requested_exit_time"])
            delta_seconds = (exit_dt - entry_dt).total_seconds()
            total_hours = round(delta_seconds / 3600.0, 4)

            att_date = req["date"]
            d_obj = date.fromisoformat(att_date) if isinstance(att_date, str) else att_date
            existing_sessions = await self.attendance_repo.find_sessions_for_date(
                req["employee_id"], d_obj
            )

            now = datetime.now(tz=UTC)
            if existing_sessions:
                target_session = existing_sessions[0]
                await self.attendance_repo.update(
                    target_session["attendance_id"],
                    {
                        "entry_time": entry_dt,
                        "exit_time": exit_dt,
                        "total_hours": total_hours,
                        "attendance_status": "complete",
                    },
                )
            else:
                att_id = f"ATT-{uuid.uuid4().hex[:12].upper()}"
                doc = {
                    "attendance_id": att_id,
                    "employee_id": req["employee_id"],
                    "date": att_date if isinstance(att_date, str) else att_date.isoformat(),
                    "entry_time": entry_dt,
                    "exit_time": exit_dt,
                    "total_hours": total_hours,
                    "attendance_status": "complete",
                    "created_at": now,
                    "updated_at": now,
                }
                await self.attendance_repo.create(doc)

            await self.audit_service.log(
                actor_id=reviewer_id,
                action="regularization.approve",
                resource_type="regularization",
                resource_id=request_id,
                employee_id=req["employee_id"],
                new_values={"status": "approved", "notes": decision.reviewer_notes},
            )
        else:
            await self.audit_service.log(
                actor_id=reviewer_id,
                action="regularization.reject",
                resource_type="regularization",
                resource_id=request_id,
                employee_id=req["employee_id"],
                new_values={"status": "rejected", "notes": decision.reviewer_notes},
            )

        return await self.regularization_repo.update_decision(
            request_id=request_id,
            status=decision.action,
            reviewed_by=reviewer_id,
            reviewer_notes=decision.reviewer_notes,
        )

    async def get_live_presence(self, department: str | None = None) -> dict[str, Any]:
        """Aggregate real-time presence data for all active employees."""
        from zoneinfo import ZoneInfo

        from app.services.policy_service import calculate_valid_hours_for_sessions, parse_session

        tz = ZoneInfo(self.company_tz)
        today_local = datetime.now(tz=tz).date()
        today_str = today_local.isoformat()

        # Fetch active employees
        query: dict[str, Any] = {"is_active": True}
        if department:
            query["department"] = department
        cursor = self.employee_repo.col.find(query, {"_id": 0})
        employees = await cursor.to_list(length=None)

        # Fetch attendance sessions for today
        att_cursor = self.attendance_repo.col.find(
            {"date": today_str, "is_deleted": {"$ne": True}}, {"_id": 0}
        )
        today_sessions = await att_cursor.to_list(length=None)

        # Group sessions by employee_id
        sessions_by_emp: dict[str, list[dict[str, Any]]] = {}
        for s in today_sessions:
            emp_id = s["employee_id"].upper()
            sessions_by_emp.setdefault(emp_id, []).append(s)

        # Fetch today's approved leaves
        leaves_by_emp: set[str] = set()
        if self.leave_repo:
            l_cursor = self.leave_repo.col.find(
                {
                    "status": "approved",
                    "start_date": {"$lte": today_str},
                    "end_date": {"$gte": today_str},
                },
                {"_id": 0, "employee_id": 1},
            )
            approved_leaves = await l_cursor.to_list(length=None)
            leaves_by_emp = {lv["employee_id"].upper() for lv in approved_leaves}

        employee_cards: list[dict[str, Any]] = []
        in_office_count = 0
        on_break_count = 0
        on_leave_count = 0
        absent_count = 0

        for emp in employees:
            e_id = emp["employee_id"].upper()
            emp_sessions = sessions_by_emp.get(e_id, [])
            has_leave = e_id in leaves_by_emp

            open_session = None
            for s in emp_sessions:
                if s.get("exit_time") is None:
                    open_session = s
                    break

            if has_leave:
                presence_status = "on_leave"
                on_leave_count += 1
            elif open_session is not None:
                presence_status = "in_office"
                in_office_count += 1
            elif emp_sessions:
                presence_status = "on_break"
                on_break_count += 1
            else:
                presence_status = "absent"
                absent_count += 1

            parsed_sessions = [parse_session(s) for s in emp_sessions]
            accumulated_hours = calculate_valid_hours_for_sessions(
                [ps for ps in parsed_sessions if ps.is_complete]
            )

            first_entry = None
            last_exit = None
            if emp_sessions:
                valid_entries = [s["entry_time"] for s in emp_sessions if s.get("entry_time")]
                if valid_entries:
                    first_entry_dt = min(valid_entries)
                    first_entry = (
                        first_entry_dt.astimezone(tz).strftime("%I:%M %p")
                        if first_entry_dt.tzinfo
                        else first_entry_dt.strftime("%I:%M %p")
                    )
                valid_exits = [s["exit_time"] for s in emp_sessions if s.get("exit_time")]
                if valid_exits:
                    last_exit_dt = max(valid_exits)
                    last_exit = (
                        last_exit_dt.astimezone(tz).strftime("%I:%M %p")
                        if last_exit_dt.tzinfo
                        else last_exit_dt.strftime("%I:%M %p")
                    )

            employee_cards.append(
                {
                    "employee_id": e_id,
                    "name": emp["name"],
                    "department": emp.get("department", "General"),
                    "email": emp.get("email", ""),
                    "presence_status": presence_status,
                    "first_entry": first_entry,
                    "last_exit": last_exit,
                    "accumulated_hours": round(accumulated_hours, 2),
                }
            )

        return {
            "date": today_str,
            "total_active_employees": len(employees),
            "in_office_count": in_office_count,
            "on_break_count": on_break_count,
            "on_leave_count": on_leave_count,
            "absent_count": absent_count,
            "employees": employee_cards,
        }
