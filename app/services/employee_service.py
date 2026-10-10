"""Employee service — business logic layer."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.repositories.employee_repo import EmployeeRepository
from app.schemas.employee import EmployeeCreate, EmployeeListParams, EmployeeUpdate

logger = logging.getLogger(__name__)


class EmployeeService:
    def __init__(self, repo: EmployeeRepository) -> None:
        self.repo = repo

    async def create_employee(self, data: EmployeeCreate) -> dict[str, Any]:
        emp_id = data.employee_id
        if not emp_id or emp_id.strip().upper() == "STRING":
            emp_id = await self.repo.next_employee_id()

        now = datetime.now(tz=UTC)
        doc = {
            "employee_id": emp_id,
            "name": data.name,
            "email": data.email,
            "department": data.department,
            "role": data.role,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        created = await self.repo.create(doc)
        logger.info("Employee created: %s", emp_id)
        return created

    async def get_employee(self, employee_id: str) -> dict[str, Any]:
        return await self.repo.get_or_raise(employee_id.upper())

    async def list_employees(self, params: EmployeeListParams) -> tuple[list[dict[str, Any]], int]:
        skip = (params.page - 1) * params.page_size
        return await self.repo.list_employees(
            skip=skip,
            limit=params.page_size,
            department=params.department,
            is_active=params.is_active,
            search=params.search,
        )

    async def update_employee(self, employee_id: str, data: EmployeeUpdate) -> dict[str, Any]:
        updates = data.model_dump(exclude_none=True)
        if not updates:
            return await self.repo.get_or_raise(employee_id.upper())
        updated = await self.repo.update(employee_id.upper(), updates)
        logger.info("Employee updated: %s", employee_id)
        return updated

    async def deactivate_employee(self, employee_id: str) -> dict[str, Any]:
        result = await self.repo.deactivate(employee_id.upper())
        logger.info("Employee deactivated: %s", employee_id)
        return result
