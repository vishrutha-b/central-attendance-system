"""
Tests for leave and holiday endpoints (/api/v1/leave and /api/v1/holidays).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_leave_success(async_client: AsyncClient, auth_headers: dict[str, str]):
    payload = {
        "employee_id": "EMP-001",
        "leave_type": "annual",
        "start_date": "2026-04-01",
        "end_date": "2026-04-03",
        "reason": "Vacation and rest",
    }
    now = datetime.now(UTC)
    mock_leave = {
        "leave_id": "LV-100",
        "employee_id": "EMP-001",
        "leave_type": "annual",
        "start_date": date(2026, 4, 1),
        "end_date": date(2026, 4, 3),
        "reason": "Vacation and rest",
        "status": "pending",
        "reviewed_by": None,
        "review_note": None,
        "created_at": now,
        "updated_at": now,
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
            "app.repositories.leave_repo.LeaveRepository.find_overlapping", new_callable=AsyncMock
        ) as mock_ov,
        patch(
            "app.repositories.leave_repo.LeaveRepository.create", new_callable=AsyncMock
        ) as mock_create,
        patch("app.repositories.admin_repo.AuditRepository.create", new_callable=AsyncMock),
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = {"employee_id": "EMP-001", "is_active": True}
        mock_ov.return_value = []
        mock_create.return_value = mock_leave

        response = await async_client.post("/api/v1/leave", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["leave_id"] == "LV-100"
        assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_approve_leave(async_client: AsyncClient, auth_headers: dict[str, str]):
    now = datetime.now(UTC)
    mock_updated = {
        "leave_id": "LV-100",
        "employee_id": "EMP-001",
        "leave_type": "annual",
        "start_date": date(2026, 4, 1),
        "end_date": date(2026, 4, 3),
        "reason": "Vacation and rest",
        "status": "approved",
        "reviewed_by": "ADM-TEST-001",
        "review_note": "Approved by HR",
        "created_at": now,
        "updated_at": now,
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
            "app.repositories.leave_repo.LeaveRepository.get_or_raise", new_callable=AsyncMock
        ) as mock_get,
        patch(
            "app.repositories.leave_repo.LeaveRepository.update_status", new_callable=AsyncMock
        ) as mock_update,
        patch("app.repositories.admin_repo.AuditRepository.create", new_callable=AsyncMock),
    ):
        mock_admin_find.return_value = mock_admin
        mock_get.return_value = {
            "leave_id": "LV-100",
            "employee_id": "EMP-001",
            "status": "pending",
        }
        mock_update.return_value = mock_updated

        response = await async_client.patch(
            "/api/v1/leave/LV-100/approve",
            json={"note": "Approved by HR"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"


@pytest.mark.asyncio
async def test_create_holiday_success(async_client: AsyncClient, auth_headers: dict[str, str]):
    now = datetime.now(UTC)
    payload = {
        "name": "Labor Day",
        "date": "2026-05-01",
        "description": "International Workers' Day",
    }
    mock_hol = {
        "holiday_id": "HOL-2026-05-01",
        "name": "Labor Day",
        "date": date(2026, 5, 1),
        "description": "International Workers' Day",
        "created_at": now,
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
            "app.repositories.leave_repo.HolidayRepository.find_by_date", new_callable=AsyncMock
        ) as mock_find,
        patch(
            "app.repositories.leave_repo.HolidayRepository.create", new_callable=AsyncMock
        ) as mock_create,
        patch("app.repositories.admin_repo.AuditRepository.create", new_callable=AsyncMock),
    ):
        mock_admin_find.return_value = mock_admin
        mock_find.return_value = None
        mock_create.return_value = mock_hol

        response = await async_client.post("/api/v1/holidays", json=payload, headers=auth_headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Labor Day"
        assert data["date"] == "2026-05-01"
