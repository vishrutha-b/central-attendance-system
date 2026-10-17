"""Regularization repository for attendance correction requests with multi-tenant isolation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument

from app.exceptions import RegularizationNotFoundError

logger = logging.getLogger(__name__)


class RegularizationRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.regularization_requests
        self.tenant_id = tenant_id

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc["tenant_id"] = self.tenant_id
        await self.col.insert_one(doc)
        return doc

    async def find_by_id(self, request_id: str) -> dict[str, Any] | None:
        return await self.col.find_one(
            {"tenant_id": self.tenant_id, "request_id": request_id},
            {"_id": 0},
        )

    async def get_or_raise(self, request_id: str) -> dict[str, Any]:
        doc = await self.find_by_id(request_id)
        if doc is None:
            raise RegularizationNotFoundError(f"Regularization request '{request_id}' not found.")
        return doc

    async def update_decision(
        self, request_id: str, status: str, reviewed_by: str, reviewer_notes: str | None = None
    ) -> dict[str, Any]:
        doc = await self.col.find_one_and_update(
            {"tenant_id": self.tenant_id, "request_id": request_id},
            {
                "$set": {
                    "status": status,
                    "reviewed_by": reviewed_by,
                    "reviewer_notes": reviewer_notes,
                    "updated_at": datetime.now(tz=UTC),
                }
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        if doc is None:
            raise RegularizationNotFoundError(f"Regularization request '{request_id}' not found.")
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
