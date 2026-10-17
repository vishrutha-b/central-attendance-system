"""Tenant repository — async MongoDB CRUD for organizations/tenants."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.exceptions import ConflictError, NotFoundError

logger = logging.getLogger(__name__)


class TenantNotFoundError(NotFoundError):
    """Raised when a tenant organization does not exist."""

    pass


class TenantRepository:
    def __init__(self, db: Any) -> None:
        self.col = db.tenants

    async def create(self, doc: dict[str, Any]) -> dict[str, Any]:
        """Create a new tenant document."""
        now = datetime.now(UTC)
        doc.setdefault("created_at", now)
        doc.setdefault("updated_at", now)
        doc.setdefault("status", "active")
        try:
            await self.col.insert_one(doc)
            return doc
        except DuplicateKeyError as exc:
            raise ConflictError(f"Tenant '{doc.get('tenant_id')}' already exists.") from exc

    async def find_by_id(self, tenant_id: str) -> dict[str, Any] | None:
        """Find a tenant by its unique identifier (slug)."""
        return await self.col.find_one({"tenant_id": tenant_id}, {"_id": 0})

    async def get_or_raise(self, tenant_id: str) -> dict[str, Any]:
        """Fetch tenant or raise TenantNotFoundError."""
        tenant = await self.find_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundError(f"Tenant '{tenant_id}' not found.")
        return tenant

    async def list_tenants(
        self,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """List tenants with pagination and optional status filter."""
        query: dict[str, Any] = {}
        if status:
            query["status"] = status

        total = await self.col.count_documents(query)
        cursor = self.col.find(query, {"_id": 0}).skip(skip).limit(limit).sort("created_at", -1)
        items = await cursor.to_list(length=limit)
        return items, total

    async def update(self, tenant_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Update tenant metadata or settings."""
        fields["updated_at"] = datetime.now(UTC)
        doc = await self.col.find_one_and_update(
            {"tenant_id": tenant_id},
            {"$set": fields},
            projection={"_id": 0},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            raise TenantNotFoundError(f"Tenant '{tenant_id}' not found.")
        return doc

    async def ensure_default_tenant(
        self, default_settings: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Idempotently seed the default tenant if none exists."""
        default_id = "default"
        existing = await self.find_by_id(default_id)
        if existing:
            return existing

        now = datetime.now(UTC)
        doc = {
            "tenant_id": default_id,
            "name": "Default Organization",
            "contact_email": "admin@company.com",
            "status": "active",
            "settings": default_settings or {},
            "created_at": now,
            "updated_at": now,
        }
        try:
            await self.col.insert_one(doc)
            logger.info("Created default organization tenant ('%s').", default_id)
            return doc
        except DuplicateKeyError:
            return (await self.find_by_id(default_id)) or doc
