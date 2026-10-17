"""Leave balance repository with multi-tenant isolation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo import ReturnDocument

logger = logging.getLogger(__name__)

DEFAULT_LEAVE_ALLOCATIONS: dict[str, float] = {
    "annual": 15.0,
    "casual": 12.0,
    "sick": 10.0,
    "other": 5.0,
}


class LeaveBalanceRepository:
    def __init__(self, db: Any, tenant_id: str = "default") -> None:
        self.col = db.leave_balances
        self.tenant_id = tenant_id

    async def get_balance(
        self, employee_id: str, year: int, leave_type: str
    ) -> dict[str, Any] | None:
        return await self.col.find_one(
            {
                "tenant_id": self.tenant_id,
                "employee_id": employee_id,
                "year": year,
                "leave_type": leave_type.lower(),
            },
            {"_id": 0},
        )

    async def get_balances_for_employee(self, employee_id: str, year: int) -> list[dict[str, Any]]:
        cursor = self.col.find(
            {"tenant_id": self.tenant_id, "employee_id": employee_id, "year": year},
            {"_id": 0},
        )
        balances = await cursor.to_list(length=None)
        if not balances:
            # Auto-initialize default corporate balances if none exist yet
            await self.initialize_defaults(employee_id, year)
            cursor = self.col.find(
                {"tenant_id": self.tenant_id, "employee_id": employee_id, "year": year},
                {"_id": 0},
            )
            balances = await cursor.to_list(length=None)
        return balances

    async def initialize_defaults(self, employee_id: str, year: int) -> None:
        now = datetime.now(tz=UTC)
        for lt, alloc in DEFAULT_LEAVE_ALLOCATIONS.items():
            await self.col.update_one(
                {
                    "tenant_id": self.tenant_id,
                    "employee_id": employee_id,
                    "year": year,
                    "leave_type": lt,
                },
                {
                    "$setOnInsert": {
                        "tenant_id": self.tenant_id,
                        "employee_id": employee_id,
                        "year": year,
                        "leave_type": lt,
                        "allocated_days": alloc,
                        "used_days": 0.0,
                        "created_at": now,
                    },
                    "$set": {"updated_at": now},
                },
                upsert=True,
            )

    async def upsert_allocation(
        self, employee_id: str, year: int, leave_type: str, allocated_days: float
    ) -> dict[str, Any]:
        now = datetime.now(tz=UTC)
        doc = await self.col.find_one_and_update(
            {
                "tenant_id": self.tenant_id,
                "employee_id": employee_id,
                "year": year,
                "leave_type": leave_type.lower(),
            },
            {
                "$set": {
                    "allocated_days": allocated_days,
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "tenant_id": self.tenant_id,
                    "employee_id": employee_id,
                    "year": year,
                    "leave_type": leave_type.lower(),
                    "used_days": 0.0,
                    "created_at": now,
                },
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
        return doc

    async def deduct_days(
        self, employee_id: str, year: int, leave_type: str, days: float
    ) -> dict[str, Any] | None:
        now = datetime.now(tz=UTC)
        return await self.col.find_one_and_update(
            {
                "tenant_id": self.tenant_id,
                "employee_id": employee_id,
                "year": year,
                "leave_type": leave_type.lower(),
            },
            {
                "$inc": {"used_days": days},
                "$set": {"updated_at": now},
            },
            return_document=ReturnDocument.AFTER,
            projection={"_id": 0},
        )
