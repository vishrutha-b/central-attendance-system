"""Leave and Holiday service."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.exceptions import LeaveConflictError, LeaveTransitionError
from app.repositories.employee_repo import EmployeeRepository
from app.repositories.leave_repo import HolidayRepository, LeaveRepository
from app.schemas.leave import HolidayCreate, LeaveDecision, LeaveRequestCreate
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class LeaveService:
    def __init__(
        self,
        leave_repo: LeaveRepository,
        employee_repo: EmployeeRepository,
        audit_service: AuditService,
    ) -> None:
        self.leave_repo = leave_repo
        self.employee_repo = employee_repo
        self.audit_service = audit_service

    async def create_leave_request(self, data: LeaveRequestCreate, actor_id: str) -> dict[str, Any]:
        employee = await self.employee_repo.get_or_raise(data.employee_id)
        if not employee["is_active"]:
            from app.exceptions import EmployeeInactiveError

            raise EmployeeInactiveError()

        # Check overlapping approved/pending requests
        overlapping = await self.leave_repo.find_overlapping(
            data.employee_id, data.start_date, data.end_date
        )
        if overlapping:
            raise LeaveConflictError(
                f"Overlapping leave request exists ({overlapping[0]['leave_id']})."
            )

        now = datetime.now(tz=UTC)
        doc = {
            "leave_id": f"LV-{uuid.uuid4().hex[:10].upper()}",
            "employee_id": data.employee_id,
            "leave_type": data.leave_type,
            "start_date": data.start_date.isoformat(),
            "end_date": data.end_date.isoformat(),
            "reason": data.reason,
            "status": "pending",
            "reviewed_by": None,
            "review_note": None,
            "created_at": now,
            "updated_at": now,
        }
        created = await self.leave_repo.create(doc)
        logger.info("Leave request created: %s for %s", doc["leave_id"], data.employee_id)

        await self.audit_service.log(
            actor_id=actor_id,
            action="leave.create",
            resource_type="leave_request",
            resource_id=str(doc["leave_id"]),
            employee_id=data.employee_id,
        )
        return created

    async def approve_leave(
        self, leave_id: str, decision: LeaveDecision, approver_id: str
    ) -> dict[str, Any]:
        leave = await self.leave_repo.get_or_raise(leave_id)
        if leave["status"] != "pending":
            raise LeaveTransitionError(f"Cannot approve leave in status '{leave['status']}'.")

        updated = await self.leave_repo.update_status(
            leave_id, "approved", approver_id, decision.note
        )
        await self.audit_service.log(
            actor_id=approver_id,
            action="leave.approve",
            resource_type="leave_request",
            resource_id=leave_id,
            employee_id=leave["employee_id"],
            previous_values={"status": "pending"},
            new_values={"status": "approved", "note": decision.note},
        )
        return updated

    async def reject_leave(
        self, leave_id: str, decision: LeaveDecision, approver_id: str
    ) -> dict[str, Any]:
        leave = await self.leave_repo.get_or_raise(leave_id)
        if leave["status"] not in ("pending",):
            raise LeaveTransitionError(f"Cannot reject leave in status '{leave['status']}'.")

        updated = await self.leave_repo.update_status(
            leave_id, "rejected", approver_id, decision.note
        )
        await self.audit_service.log(
            actor_id=approver_id,
            action="leave.reject",
            resource_type="leave_request",
            resource_id=leave_id,
            employee_id=leave["employee_id"],
            previous_values={"status": "pending"},
            new_values={"status": "rejected", "note": decision.note},
        )
        return updated

    async def list_leave_requests(
        self,
        page: int = 1,
        page_size: int = 20,
        employee_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        skip = (page - 1) * page_size
        return await self.leave_repo.list_requests(
            skip=skip, limit=page_size, employee_id=employee_id, status=status
        )

    async def get_approved_leave_dates(
        self, employee_id: str, start_date: date, end_date: date
    ) -> set[date]:
        """Return all individual approved leave dates in the range."""
        leaves = await self.leave_repo.find_approved_in_range(employee_id, start_date, end_date)
        dates: set[date] = set()
        for leave in leaves:
            ls = (
                date.fromisoformat(leave["start_date"])
                if isinstance(leave["start_date"], str)
                else leave["start_date"]
            )
            le = (
                date.fromisoformat(leave["end_date"])
                if isinstance(leave["end_date"], str)
                else leave["end_date"]
            )
            d = max(ls, start_date)
            while d <= min(le, end_date):
                dates.add(d)
                d += timedelta(days=1)
        return dates


class HolidayService:
    def __init__(self, holiday_repo: HolidayRepository) -> None:
        self.holiday_repo = holiday_repo

    async def create_holiday(self, data: HolidayCreate) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        doc = {
            "holiday_id": f"HOL-{uuid.uuid4().hex[:10].upper()}",
            "name": data.name,
            "date": data.date.isoformat(),
            "description": data.description,
            "created_at": now,
        }
        return await self.holiday_repo.create(doc)

    async def list_holidays(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        return await self.holiday_repo.list_holidays(start_date, end_date)

    async def get_holiday_dates(self, start_date: date, end_date: date) -> set[date]:
        holidays = await self.holiday_repo.find_in_range(start_date, end_date)
        return {
            date.fromisoformat(h["date"]) if isinstance(h["date"], str) else h["date"]
            for h in holidays
        }
