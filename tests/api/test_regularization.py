"""Tests for attendance regularization endpoints."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_regularization_success(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    payload = {
        "employee_id": "EMP-001",
        "date": "2026-04-01",
        "requested_entry_time": "09:00",
        "requested_exit_time": "18:00",
        "reason": "forgot_punch",
        "notes": "Forgot to clock out before leaving.",
    }
    now = datetime.now(UTC)
    mock_reg = {
        "request_id": "REG-12345",
        "employee_id": "EMP-001",
        "date": "2026-04-01",
        "requested_entry_time": "2026-04-01T03:30:00+00:00",
        "requested_exit_time": "2026-04-01T12:30:00+00:00",
        "reason": "forgot_punch",
        "notes": "Forgot to clock out before leaving.",
        "status": "pending",
        "reviewed_by": None,
        "reviewer_notes": None,
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
            "app.repositories.regularization_repo.RegularizationRepository.create",
            new_callable=AsyncMock,
        ) as mock_create,
        patch("app.repositories.admin_repo.AuditRepository.create", new_callable=AsyncMock),
    ):
        mock_admin_find.return_value = mock_admin
        mock_emp.return_value = {"employee_id": "EMP-001", "is_active": True}
        mock_create.return_value = mock_reg

        response = await async_client.post(
            "/api/v1/attendance/regularize",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["request_id"] == "REG-12345"
        assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_review_regularization_approve(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    decision_payload = {
        "action": "approved",
        "reviewer_notes": "Verified with team lead.",
    }
    now = datetime.now(UTC)
    existing_reg = {
        "request_id": "REG-12345",
        "employee_id": "EMP-001",
        "date": "2026-04-01",
        "requested_entry_time": "2026-04-01T03:30:00+00:00",
        "requested_exit_time": "2026-04-01T12:30:00+00:00",
        "reason": "forgot_punch",
        "status": "pending",
        "created_at": now,
        "updated_at": now,
    }
    updated_reg = {
        **existing_reg,
        "status": "approved",
        "reviewed_by": "ADM-TEST-001",
        "reviewer_notes": "Verified with team lead.",
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
            "app.repositories.regularization_repo.RegularizationRepository.get_or_raise",
            new_callable=AsyncMock,
        ) as mock_get,
        patch(
            "app.repositories.attendance_repo.AttendanceRepository.find_sessions_for_date",
            new_callable=AsyncMock,
        ) as mock_find_sessions,
        patch(
            "app.repositories.attendance_repo.AttendanceRepository.create", new_callable=AsyncMock
        ) as mock_att_create,
        patch(
            "app.repositories.regularization_repo.RegularizationRepository.update_decision",
            new_callable=AsyncMock,
        ) as mock_decision,
        patch("app.repositories.admin_repo.AuditRepository.create", new_callable=AsyncMock),
    ):
        mock_admin_find.return_value = mock_admin
        mock_get.return_value = existing_reg
        mock_find_sessions.return_value = []
        mock_att_create.return_value = {}
        mock_decision.return_value = updated_reg

        response = await async_client.post(
            "/api/v1/attendance/regularize/REG-12345/decision",
            json=decision_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["reviewed_by"] == "ADM-TEST-001"
