"""
Tests for reporting endpoints (/api/v1/reports/attendance and CSV export).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_report_invalid_period(async_client: AsyncClient, auth_headers: dict[str, str]):
    mock_admin = {
        "admin_id": "ADM-TEST-001",
        "username": "testadmin",
        "role": "admin",
        "is_active": True,
    }

    with patch(
        "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
    ) as mock_admin_find:
        mock_admin_find.return_value = mock_admin

        response = await async_client.get(
            "/api/v1/reports/attendance?period=hourly",
            headers=auth_headers,
        )
        assert response.status_code == 422


@pytest.mark.asyncio
async def test_report_daily_success(async_client: AsyncClient, auth_headers: dict[str, str]):
    mock_report = {
        "period": "daily",
        "period_start": "2026-03-10",
        "period_end": "2026-03-10",
        "summary": {
            "total_employees": 1,
            "active_employees": 1,
            "inactive_employees": 0,
            "overall_compliant": 1,
            "overall_non_compliant": 0,
            "overall_incomplete_session_count": 0,
            "overall_no_attendance_count": 0,
        },
        "employees": [
            {
                "employee_id": "EMP-001",
                "name": "Aarav Sharma",
                "email": "aarav@company.com",
                "department": "Engineering",
                "is_active": True,
                "total_days_attended": 1,
                "total_valid_hours": 8.0,
                "avg_hours_per_attended_day": 8.0,
                "completed_sessions": 1,
                "incomplete_sessions": 0,
                "invalid_sessions": 0,
                "has_no_attendance": False,
                "weekly_compliance": [],
                "approved_leave_dates": [],
                "holiday_dates": [],
            }
        ],
        "pagination": {"page": 1, "page_size": 20, "total": 1, "total_pages": 1},
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
            "app.services.report_service.ReportService.generate_report", new_callable=AsyncMock
        ) as mock_gen,
    ):
        mock_admin_find.return_value = mock_admin
        mock_gen.return_value = mock_report

        response = await async_client.get(
            "/api/v1/reports/attendance?period=daily&date=2026-03-10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "daily"
        assert len(data["employees"]) == 1
        assert data["employees"][0]["employee_id"] == "EMP-001"


@pytest.mark.asyncio
async def test_report_csv_export(async_client: AsyncClient, auth_headers: dict[str, str]):
    mock_report = {
        "employees": [
            {
                "employee_id": "EMP-001",
                "name": "Aarav Sharma",
                "email": "aarav@company.com",
                "department": "Engineering",
                "is_active": True,
                "total_days_attended": 1,
                "total_valid_hours": 8.0,
                "avg_hours_per_attended_day": 8.0,
                "completed_sessions": 1,
                "incomplete_sessions": 0,
                "invalid_sessions": 0,
                "has_no_attendance": False,
                "weekly_compliance": [],
                "approved_leave_dates": [],
                "holiday_dates": [],
            }
        ]
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
            "app.services.report_service.ReportService.generate_report", new_callable=AsyncMock
        ) as mock_gen,
    ):
        mock_admin_find.return_value = mock_admin
        mock_gen.return_value = mock_report

        response = await async_client.get(
            "/api/v1/reports/attendance/export.csv?period=daily&date=2026-03-10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "Employee ID" in response.text
        assert "EMP-001" in response.text
