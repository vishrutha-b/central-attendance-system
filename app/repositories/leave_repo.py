"""Leave and Holiday repositories with multi-tenant isolation."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.exceptions import (
    ConflictError,
    HolidayConflictError,
    LeaveNotFoundError,
)

logger = logging.getLogger(__name__)


class LeaveRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.leave_requests
        self.tenant_id = tenant_id

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc["tenant_id"] = self.tenant_id
        try:
            await self.col.insert_one(doc)
            return doc
        except DuplicateKeyError as exc:
            raise ConflictError("Duplicate leave request.") from exc

    async def find_by_id(self, leave_id: str) -> dict[str, Any] | None:
        return await self.col.find_one(
            {"tenant_id": self.tenant_id, "leave_id": leave_id},
            {"_id": 0},
        )

    async def get_or_raise(self, leave_id: str) -> dict[str, Any]:
        doc = await self.find_by_id(leave_id)
        if doc is None:
            raise LeaveNotFoundError(f"Leave request '{leave_id}' not found.")
        return doc

    async def find_overlapping(
        self, employee_id: str, start_date: date, end_date: date, exclude_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Find approved/pending leaves that overlap the given date range for this tenant."""
        query: dict[str, Any] = {
            "tenant_id": self.tenant_id,
            "employee_id": employee_id,
            "status": {"$in": ["pending", "approved"]},
            "start_date": {"$lte": end_date.isoformat()},
            "end_date": {"$gte": start_date.isoformat()},
        }
        if exclude_id:
            query["leave_id"] = {"$ne": exclude_id}
        cursor = self.col.find(query, {"_id": 0})
        return await cursor.to_list(length=None)

    async def update_status(
        self, leave_id: str, status: str, reviewed_by: str, note: str | None
    ) -> dict[str, Any]:
        doc = await self.col.find_one_and_update(
            {"tenant_id": self.tenant_id, "leave_id": leave_id},
            {
                "$set": {
                    "status": status,
                    "reviewed_by": reviewed_by,
                    "review_note": note,
                    "updated_at": datetime.now(tz=UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if doc is None:
            raise LeaveNotFoundError(f"Leave request '{leave_id}' not found.")
        return doc

    async def list_requests(
        self,
        skip: int = 0,
        limit: int = 20,
        employee_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"tenant_id": self.tenant_id}
        if employee_id:
            query["employee_id"] = employee_id
        if status:
            query["status"] = status

        total = await self.col.count_documents(query)
        cursor = self.col.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        return items, total

    async def find_approved_in_range(
        self, employee_id: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        query = {
            "tenant_id": self.tenant_id,
            "employee_id": employee_id,
            "status": "approved",
            "start_date": {"$lte": end_date.isoformat()},
            "end_date": {"$gte": start_date.isoformat()},
        }
        cursor = self.col.find(query, {"_id": 0})
        return await cursor.to_list(length=None)


class HolidayRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.holidays
        self.tenant_id = tenant_id

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc["tenant_id"] = self.tenant_id
        try:
            await self.col.insert_one(doc)
            return doc
        except DuplicateKeyError as exc:
            raise HolidayConflictError("A holiday already exists on this date.") from exc

    async def find_by_date(self, holiday_date: date) -> dict[str, Any] | None:
        return await self.col.find_one(
            {"tenant_id": self.tenant_id, "date": holiday_date.isoformat()},
            {"_id": 0},
        )

    async def list_holidays(
        self, start_date: date | None = None, end_date: date | None = None
    ) -> list[dict[str, Any]]:
        query: dict[str, Any] = {"tenant_id": self.tenant_id}
        if start_date or end_date:
            date_filter: dict[str, Any] = {}
            if start_date:
                date_filter["$gte"] = start_date.isoformat()
            if end_date:
                date_filter["$lte"] = end_date.isoformat()
            query["date"] = date_filter
        cursor = self.col.find(query, {"_id": 0}).sort("date", 1)
        return await cursor.to_list(length=None)

    async def find_in_range(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        return await self.list_holidays(start_date, end_date)
