"""Admin user, audit log, and notification repositories with multi-tenant isolation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo.errors import DuplicateKeyError

from app.exceptions import AdminNotFoundError, ConflictError

logger = logging.getLogger(__name__)


class AdminRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.admin_users
        self.tenant_id = tenant_id

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc["tenant_id"] = self.tenant_id
        try:
            await self.col.insert_one(doc)
            return doc
        except DuplicateKeyError as exc:
            raise ConflictError(
                "Admin with this username or email already exists for this tenant."
            ) from exc

    async def find_by_username(self, username: str) -> dict[str, Any] | None:
        return await self.col.find_one(
            {"tenant_id": self.tenant_id, "username": username},
            {"_id": 0},
        )

    async def find_by_email(self, email: str) -> dict[str, Any] | None:
        return await self.col.find_one(
            {"tenant_id": self.tenant_id, "email": email.lower()},
            {"_id": 0},
        )

    async def find_by_id(self, admin_id: str) -> dict[str, Any] | None:
        return await self.col.find_one(
            {"tenant_id": self.tenant_id, "admin_id": admin_id},
            {"_id": 0},
        )

    async def list_admins(self) -> list[dict[str, Any]]:
        cursor = self.col.find(
            {"tenant_id": self.tenant_id},
            {"_id": 0, "hashed_password": 0},
        ).sort("created_at", -1)
        return await cursor.to_list(length=None)

    async def get_or_raise(self, admin_id: str) -> dict[str, Any]:
        doc = await self.find_by_id(admin_id)
        if doc is None:
            raise AdminNotFoundError(f"Admin '{admin_id}' not found.")
        return doc

    async def count(self) -> int:
        return await self.col.count_documents({"tenant_id": self.tenant_id})


class AuditRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.audit_logs
        self.tenant_id = tenant_id

    async def create(self, doc: dict[str, Any]) -> None:
        doc["tenant_id"] = self.tenant_id
        try:
            await self.col.insert_one(doc)
        except Exception as exc:
            # Audit logs must not crash the application
            logger.error("Failed to write audit log: %s", exc)

    async def list_logs(
        self,
        skip: int = 0,
        limit: int = 20,
        resource_type: str | None = None,
        actor_id: str | None = None,
        employee_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        query: dict[str, Any] = {"tenant_id": self.tenant_id}
        if resource_type:
            query["resource_type"] = resource_type
        if actor_id:
            query["actor_id"] = actor_id
        if employee_id:
            query["employee_id"] = employee_id

        total = await self.col.count_documents(query)
        cursor = self.col.find(query, {"_id": 0}).sort("timestamp", -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
        return items, total


class NotificationRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.notification_logs
        self.tenant_id = tenant_id

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        doc["tenant_id"] = self.tenant_id
        try:
            await self.col.insert_one(doc)
            return doc
        except DuplicateKeyError:
            # Already exists — return existing
            existing = await self.col.find_one(
                {"tenant_id": self.tenant_id, "dedup_key": doc["dedup_key"]},
                {"_id": 0},
            )
            return existing or doc

    async def find_by_dedup_key(self, dedup_key: str) -> dict[str, Any] | None:
        return await self.col.find_one(
            {"tenant_id": self.tenant_id, "dedup_key": dedup_key},
            {"_id": 0},
        )

    async def find_pending_retries(self) -> list[dict[str, Any]]:
        now = datetime.now(tz=UTC)
        query: dict[str, Any] = {
            "status": "pending_retry",
            "next_retry_at": {"$lte": now},
        }
        if self.tenant_id:
            query["tenant_id"] = self.tenant_id
        cursor = self.col.find(query, {"_id": 0}).limit(100)
        return await cursor.to_list(length=100)

    async def update(self, notification_id: str, updates: dict[str, Any]) -> None:
        updates["updated_at"] = datetime.now(tz=UTC)
        await self.col.update_one(
            {"tenant_id": self.tenant_id, "notification_id": notification_id},
            {"$set": updates},
        )
