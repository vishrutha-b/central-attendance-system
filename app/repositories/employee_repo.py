"""Employee repository — async MongoDB CRUD."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.exceptions import ConflictError, EmployeeNotFoundError

logger = logging.getLogger(__name__)


class EmployeeRepository:
    def __init__(self, db: Any) -> None:
        self.col = db.employees

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        try:
            await self.col.insert_one(doc)
            return doc
        except DuplicateKeyError as exc:
            key = _extract_dup_key(exc)
            raise ConflictError(f"Employee with duplicate {key} already exists.") from exc

    async def find_by_id(self, employee_id: str) -> dict[str, Any] | None:
        return await self.col.find_one({"employee_id": employee_id}, {"_id": 0})

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.col.find_one({"email": email.lower()}, {"_id": 0})

    async def get_or_raise(self, employee_id: str) -> dict[str, Any]:
        doc = await self.find_by_id(employee_id)
        if doc is None:
            raise EmployeeNotFoundError(f"Employee '{employee_id}' not found.")
        return doc

    async def list_employees(
        self,
        skip: int = 0,
        limit: int = 20,
        department: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {}
        if department:
            query["department"] = department
        if is_active is not None:
            query["is_active"] = is_active
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
                {"employee_id": {"$regex": search, "$options": "i"}},
            ]

        total = await self.col.count_documents(query)
        cursor = self.col.find(query, {"_id": 0}).skip(skip).limit(limit).sort("name", 1)
        items = await cursor.to_list(length=limit)
        return items, total

    async def update(self, employee_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        updates["updated_at"] = datetime.now(tz=UTC)
        try:
            doc = await self.col.find_one_and_update(
                {"employee_id": employee_id},
                {"$set": updates},
                return_document=ReturnDocument.AFTER,
                projection={"_id": 0},
            )
        except DuplicateKeyError as exc:
            key = _extract_dup_key(exc)
            raise ConflictError(f"Update conflicts with existing employee {key}.") from exc

        if doc is None:
            raise EmployeeNotFoundError(f"Employee '{employee_id}' not found.")
        return doc

    async def deactivate(self, employee_id: str) -> dict[str, Any]:
        return await self.update(employee_id, {"is_active": False})

    async def get_active_employees(self) -> list[dict[str, Any]]:
        cursor = self.col.find({"is_active": True}, {"_id": 0}).sort("employee_id", 1)
        return await cursor.to_list(length=None)

    async def next_employee_id(self) -> str:
        count = await self.col.count_documents({})
        cand_num = count + 1
        while True:
            candidate = f"EMP-{cand_num:03d}"
            existing = await self.find_by_id(candidate)
            if existing is None:
                return candidate
            cand_num += 1


def _extract_dup_key(exc: DuplicateKeyError) -> str:
    """Try to extract the duplicate key name from the error details."""
    try:
        details = exc.details or {}
        key_value = details.get("keyValue", {})
        return list(key_value.keys())[0] if key_value else "field"
    except Exception:
        return "field"
