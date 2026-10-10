"""Employee management routes."""

from __future__ import annotations

import logging
import math
from typing import Any

from fastapi import APIRouter, Depends, Query, status

from app.api.dependencies import get_current_admin, get_employee_service, require_admin
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeListParams,
    EmployeeResponse,
    EmployeeUpdate,
)
from app.services.employee_service import EmployeeService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/employees", tags=["Employees"])


@router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee",
    description="Create a new employee record. Requires admin role.",
)
async def create_employee(
    data: EmployeeCreate,
    service: EmployeeService = Depends(get_employee_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return await service.create_employee(data)


@router.get(
    "",
    summary="List employees",
    description="List all employees with optional filtering and pagination.",
)
async def list_employees(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    department: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(default=None),
    service: EmployeeService = Depends(get_employee_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    params = EmployeeListParams(
        page=page,
        page_size=page_size,
        department=department,
        is_active=is_active,
        search=search,
    )
    items, total = await service.list_employees(params)
    total_pages = max(1, math.ceil(total / page_size))
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.get(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Get employee",
    description="Retrieve a single employee by employee_id.",
)
async def get_employee(
    employee_id: str,
    service: EmployeeService = Depends(get_employee_service),
    current_admin: dict[str, Any] = Depends(get_current_admin),
) -> dict[str, Any]:
    return await service.get_employee(employee_id)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeResponse,
    summary="Update employee",
    description="Partially update an employee record. Requires admin role.",
)
async def update_employee(
    employee_id: str,
    data: EmployeeUpdate,
    service: EmployeeService = Depends(get_employee_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    return await service.update_employee(employee_id, data)


@router.delete(
    "/{employee_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate employee",
    description=(
        "Soft-delete: sets is_active=False. Historical records are preserved. "
        "Requires admin role."
    ),
)
async def deactivate_employee(
    employee_id: str,
    service: EmployeeService = Depends(get_employee_service),
    current_admin: dict[str, Any] = Depends(require_admin),
) -> dict[str, Any]:
    result = await service.deactivate_employee(employee_id)
    return {"message": f"Employee '{employee_id}' deactivated.", "employee": result}
