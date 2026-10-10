"""Audit log service."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from app.repositories.admin_repo import AuditRepository

logger = logging.getLogger(__name__)


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def log(
        self,
        actor_id: str,
        action: str,
        resource_type: str,
        resource_id: str,
        employee_id: str | None = None,
        previous_values: dict[str, Any] | None = None,
        new_values: dict[str, Any] | None = None,
        outcome: str = "success",
        correlation_id: str | None = None,
    ) -> None:
        """Write an immutable audit log entry."""
        doc = {
            "audit_id": f"AUD-{uuid.uuid4().hex[:12].upper()}",
            "actor_id": actor_id,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "employee_id": employee_id,
            "previous_values": previous_values,
            "new_values": new_values,
            "outcome": outcome,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(tz=UTC),
        }
        await self.repo.create(doc)
