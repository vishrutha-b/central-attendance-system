"""Tests for leave balance endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_leave_balances_success(async_client: AsyncClient, auth_headers: dict[str, str]):
    mock_balances = [
        {"leave_type": "annual", "allocated_days": 15.0, "used_days": 2.0},
        {"leave_type": "casual", "allocated_days": 12.0, "used_days": 0.0},
        {"leave_type": "sick", "allocated_days": 10.0, "used_days": 1.0},
    ]

    mock_admin = {
        "admin_id": "ADM-TEST-001",
        "username": "testadmin",
        "role": "admin",
        "is_active": True,
    }

    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
        ) as mock_admin_find,
        patch(
            "app.repositories.employee_repo.EmployeeRepository.get_or_raise", new_callable=AsyncMock
        ) as mock_emp,
        patch(
            "app.repositories.leave_balance_repo.LeaveBalanceRepository.get_balances_for_employee",
            new_callable=AsyncMock,
        ) as mock_bal,
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = {"employee_id": "EMP-001", "is_active": True}
        mock_bal.return_value = mock_balances

        response = await async_client.get(
            "/api/v1/leave/balances/EMP-001?year=2026",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["employee_id"] == "EMP-001"
        assert len(data["balances"]) == 3
        # Annual: 15 allocated, 2 used -> 13 remaining
        assert data["balances"][0]["remaining_days"] == 13.0


@pytest.mark.asyncio
async def test_allocate_leave_balance_success(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    payload = {
        "employee_id": "EMP-001",
        "year": 2026,
        "leave_type": "casual",
        "allocated_days": 14.0,
    }
    mock_doc = {
        "employee_id": "EMP-001",
        "year": 2026,
        "leave_type": "casual",
        "allocated_days": 14.0,
        "used_days": 2.0,
    }

    mock_admin = {
        "admin_id": "ADM-TEST-001",
        "username": "testadmin",
        "role": "admin",
        "is_active": True,
    }

    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
        ) as mock_admin_find,
        patch(
            "app.repositories.employee_repo.EmployeeRepository.get_or_raise", new_callable=AsyncMock
        ) as mock_emp,
        patch(
            "app.repositories.leave_balance_repo.LeaveBalanceRepository.upsert_allocation",
            new_callable=AsyncMock,
        ) as mock_upsert,
        patch("app.repositories.admin_repo.AuditRepository.create", new_callable=AsyncMock),
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = {"employee_id": "EMP-001", "is_active": True}
        mock_upsert.return_value = mock_doc

        response = await async_client.post(
            "/api/v1/leave/balances/allocate",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["leave_type"] == "casual"
        assert data["allocated_days"] == 14.0
        assert data["remaining_days"] == 12.0
