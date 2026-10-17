"""Password reset token repository with multi-tenant scoping."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

logger = logging.getLogger(__name__)


class PasswordResetRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.password_reset_tokens
        self.tenant_id = tenant_id

    async def create_reset_token(
        self,
        user_id: str,
        user_type: str,
        email: str,
        code: str,
        expires_in_minutes: int = 15,
    ) -> dict[str, Any]:
        """Store a new verification code for password reset."""
        now = datetime.now(tz=UTC)
        expires_at = now + timedelta(minutes=expires_in_minutes)

        doc = {
            "tenant_id": self.tenant_id,
            "user_id": user_id,
            "user_type": user_type,
            "email": email.lower().strip(),
            "code": code.strip(),
            "expires_at": expires_at,
            "used": False,
            "created_at": now,
        }
        await self.col.insert_one(doc)
        logger.info(
            "Created password reset code for %s [%s] in tenant '%s'.",
            email,
            user_type,
            self.tenant_id,
        )
        return doc

    async def find_valid_token(
        self,
        email: str,
        code: str,
    ) -> dict[str, Any] | None:
        """Find an unexpired, unused reset token matching email and code."""
        now = datetime.now(tz=UTC)
        return await self.col.find_one(
            {
                "tenant_id": self.tenant_id,
                "email": email.lower().strip(),
                "code": code.strip(),
                "used": False,
                "expires_at": {"$gte": now},
            },
            {"_id": 0},
        )

    async def mark_used(self, email: str, code: str) -> bool:
        """Invalidate code after successful password change."""
        res = await self.col.update_many(
            {
                "tenant_id": self.tenant_id,
                "email": email.lower().strip(),
                "code": code.strip(),
            },
            {"$set": {"used": True, "used_at": datetime.now(tz=UTC)}},
        )
        return res.modified_count > 0
