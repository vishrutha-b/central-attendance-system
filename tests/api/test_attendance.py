"""
Tests for attendance recording and inquiry endpoints (/api/v1/attendance).
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_record_entry_success(async_client: AsyncClient, auth_headers: dict[str, str]):
    entry_payload = {
        "employee_id": "EMP-001",
        "entry_time": "2026-03-10T09:00:00Z",
    }

    now = datetime.now(UTC)
    mock_doc = {
        "attendance_id": "ATT-001",
        "employee_id": "EMP-001",
        "date": date(2026, 3, 10),
        "entry_time": datetime.fromisoformat("2026-03-10T09:00:00+00:00"),
        "exit_time": None,
        "total_hours": 0.0,
        "attendance_status": "incomplete",
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
            "app.repositories.attendance_repo.AttendanceRepository.find_open_session",
            new_callable=AsyncMock,
        ) as mock_open,
        patch(
            "app.repositories.attendance_repo.AttendanceRepository.create", new_callable=AsyncMock
        ) as mock_create,
        patch("app.repositories.admin_repo.AuditRepository.create", new_callable=AsyncMock),
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = {"employee_id": "EMP-001", "is_active": True}
        mock_open.return_value = None
        mock_create.return_value = mock_doc

        response = await async_client.post(
            "/api/v1/attendance/entry",
            json=entry_payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["attendance_id"] == "ATT-001"
        assert data["attendance_status"] == "incomplete"


@pytest.mark.asyncio
async def test_record_entry_already_open(async_client: AsyncClient, auth_headers: dict[str, str]):
    entry_payload = {
        "employee_id": "EMP-001",
        "entry_time": "2026-03-10T10:00:00Z",
    }

    existing_open = {
        "attendance_id": "ATT-OPEN",
        "employee_id": "EMP-001",
        "entry_time": datetime.fromisoformat("2026-03-10T09:00:00+00:00"),
        "exit_time": None,
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
            "app.repositories.attendance_repo.AttendanceRepository.find_open_session",
            new_callable=AsyncMock,
        ) as mock_open,
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = {"employee_id": "EMP-001", "is_active": True}
        mock_open.return_value = existing_open

        response = await async_client.post(
            "/api/v1/attendance/entry",
            json=entry_payload,
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "open session" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_record_exit_no_open_session(async_client: AsyncClient, auth_headers: dict[str, str]):
    exit_payload = {
        "employee_id": "EMP-001",
        "exit_time": "2026-03-10T17:00:00Z",
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
            "app.repositories.attendance_repo.AttendanceRepository.find_open_session",
            new_callable=AsyncMock,
        ) as mock_open,
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = {"employee_id": "EMP-001", "is_active": True}
        mock_open.return_value = None

        response = await async_client.post(
            "/api/v1/attendance/exit",
            json=exit_payload,
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "no open attendance session" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_quick_record_under_5_hours_triggers_daily_email(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    payload = {
        "employee_id": "EMP-001",
        "date": "2026-10-09",
        "entry_time": "09:00",
        "exit_time": "12:00",
    }

    mock_admin = {
        "admin_id": "ADM-TEST-001",
        "username": "testadmin",
        "role": "admin",
        "is_active": True,
    }
    mock_emp_doc = {
        "employee_id": "EMP-001",
        "name": "Jane Doe",
        "email": "jane@company.com",
        "is_active": True,
    }
    now = datetime.now(UTC)
    mock_created = {
        "attendance_id": "ATT-002",
        "employee_id": "EMP-001",
        "date": date(2026, 10, 9),
        "entry_time": datetime(2026, 10, 9, 3, 30, tzinfo=UTC),
        "exit_time": datetime(2026, 10, 9, 6, 30, tzinfo=UTC),
        "total_hours": 3.0,
        "attendance_status": "complete",
        "created_at": now,
        "updated_at": now,
    }

    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_id",
            new_callable=AsyncMock,
        ) as mock_admin_find,
        patch(
            "app.repositories.employee_repo.EmployeeRepository.get_or_raise",
            new_callable=AsyncMock,
        ) as mock_emp,
        patch(
            "app.repositories.attendance_repo.AttendanceRepository.create",
            new_callable=AsyncMock,
        ) as mock_create,
        patch(
            "app.repositories.attendance_repo.AttendanceRepository.find_sessions_for_date",
            new_callable=AsyncMock,
        ) as mock_find_sessions,
        patch(
            "app.repositories.admin_repo.AuditRepository.create",
            new_callable=AsyncMock,
        ),
        patch(
            "app.services.notification_service.NotificationService.send_daily_violation_email",
            new_callable=AsyncMock,
        ) as mock_email,
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = mock_emp_doc
        mock_create.return_value = mock_created
        mock_find_sessions.return_value = [mock_created]
        mock_email.return_value = True

        response = await async_client.post(
            "/api/v1/attendance/quick-record",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["total_hours"] == 3.0
        assert "policy_alert" in data
        assert "less than mandatory 5.0" in data["policy_alert"]
        mock_email.assert_awaited_once()
