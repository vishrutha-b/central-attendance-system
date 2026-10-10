"""Attendance repository — async MongoDB CRUD."""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.exceptions import AttendanceConflictError, AttendanceNotFoundError

logger = logging.getLogger(__name__)


class AttendanceRepository:
    def __init__(self, db: Any) -> None:
        self.col = db.attendance

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        try:
            await self.col.insert_one(doc)
            return doc
        except DuplicateKeyError as exc:
            raise AttendanceConflictError("Duplicate attendance record.") from exc

    async def find_by_id(self, attendance_id: str) -> dict[str, Any] | None:
        return await self.col.find_one({"attendance_id": attendance_id}, {"_id": 0})

    async def get_or_raise(self, attendance_id: str) -> dict[str, Any]:
        doc = await self.find_by_id(attendance_id)
        if doc is None:
            raise AttendanceNotFoundError(f"Attendance record '{attendance_id}' not found.")
        return doc

    async def find_open_session(self, employee_id: str) -> dict[str, Any] | None:
        """Return the most recent session with no exit_time."""
        cursor = (
            self.col.find(
                {"employee_id": employee_id, "exit_time": None},
                {"_id": 0},
            )
            .sort("entry_time", -1)
            .limit(1)
        )
        docs = await cursor.to_list(length=1)
        return docs[0] if docs else None

    async def find_sessions_for_date(
        self, employee_id: str, attendance_date: date
    ) -> list[dict[str, Any]]:
        query = {
            "employee_id": employee_id,
            "date": attendance_date.isoformat(),
        }
        cursor = self.col.find(query, {"_id": 0}).sort("entry_time", 1)
        return await cursor.to_list(length=None)

    async def find_sessions_in_range(
        self, employee_id: str, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        query = {
            "employee_id": employee_id,
            "date": {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat(),
            },
        }
        cursor = self.col.find(query, {"_id": 0}).sort([("date", 1), ("entry_time", 1)])
        return await cursor.to_list(length=None)

    async def find_all_in_range(self, start_date: date, end_date: date) -> list[dict[str, Any]]:
        query = {
            "date": {
                "$gte": start_date.isoformat(),
                "$lte": end_date.isoformat(),
            }
        }
        cursor = self.col.find(query, {"_id": 0}).sort([("employee_id", 1), ("date", 1)])
        return await cursor.to_list(length=None)

    async def update(self, attendance_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        updates["updated_at"] = datetime.now(tz=UTC)
        doc = await self.col.find_one_and_update(
            {"attendance_id": attendance_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if doc is None:
            raise AttendanceNotFoundError(f"Attendance record '{attendance_id}' not found.")
        return doc

    async def count_by_employee(self, employee_id: str) -> int:
        return await self.col.count_documents({"employee_id": employee_id})

    async def list_for_employee(
        self,
        employee_id: str,
        skip: int = 0,
        limit: int = 20,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"employee_id": employee_id}
        if start_date:
            query.setdefault("date", {})["$gte"] = start_date.isoformat()
        if end_date:
            query.setdefault("date", {})["$lte"] = end_date.isoformat()

        total = await self.col.count_documents(query)
        cursor = (
            self.col.find(query, {"_id": 0})
            .sort([("date", -1), ("entry_time", -1)])
            .skip(skip)
            .limit(limit)
        )
        items = await cursor.to_list(length=limit)
        return items, total
