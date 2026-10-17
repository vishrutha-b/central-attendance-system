"""Tests for live presence endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_live_presence_success(async_client: AsyncClient, auth_headers: dict[str, str]):
    mock_presence = {
        "date": "2026-04-01",
        "total_active_employees": 2,
        "in_office_count": 0,
        "on_break_count": 0,
        "on_leave_count": 0,
        "absent_count": 2,
        "employees": [
            {
                "employee_id": "EMP-001",
                "name": "Alice",
                "department": "Engineering",
                "email": "alice@company.com",
                "presence_status": "absent",
                "first_entry": None,
                "last_exit": None,
                "accumulated_hours": 0.0,
            },
            {
                "employee_id": "EMP-002",
                "name": "Bob",
                "department": "Design",
                "email": "bob@company.com",
                "presence_status": "absent",
                "first_entry": None,
                "last_exit": None,
                "accumulated_hours": 0.0,
            },
        ],
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
            "app.services.attendance_service.AttendanceService.get_live_presence",
            new_callable=AsyncMock,
        ) as mock_presence_call,
    ):
        mock_admin_find.return_value = mock_admin
        mock_presence_call.return_value = mock_presence

        response = await async_client.get(
            "/api/v1/attendance/live-presence",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_active_employees"] == 2
        assert data["absent_count"] == 2
        assert len(data["employees"]) == 2
        assert data["employees"][0]["employee_id"] == "EMP-001"
        assert data["employees"][0]["presence_status"] == "absent"
