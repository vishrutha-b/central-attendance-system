"""
Tests for employee management endpoints (/api/v1/employees).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_employee_success(async_client: AsyncClient, auth_headers: dict[str, str]):
    new_emp_payload = {
        "employee_id": "EMP-999",
        "name": "Kavita Rao",
        "email": "kavita.rao@company.com",
        "department": "Engineering",
        "role": "Engineer",
    }

    now = datetime.now(UTC)
    created_doc = {
        **new_emp_payload,
        "is_active": True,
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
            "app.repositories.employee_repo.EmployeeRepository.create", new_callable=AsyncMock
        ) as mock_create,
        patch(
            "app.repositories.employee_repo.EmployeeRepository.find_by_id", new_callable=AsyncMock
        ) as mock_find_id,
        patch(
            "app.repositories.employee_repo.EmployeeRepository.find_by_email",
            new_callable=AsyncMock,
        ) as mock_find_email,
    ):
        mock_admin_find.return_value = mock_admin
        mock_find_id.return_value = None
        mock_find_email.return_value = None
        mock_create.return_value = created_doc

        response = await async_client.post(
            "/api/v1/employees",
            json=new_emp_payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["employee_id"] == "EMP-999"
        assert data["name"] == "Kavita Rao"
        assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_employee_unauthorized(async_client: AsyncClient):
    new_emp_payload = {
        "employee_id": "EMP-999",
        "name": "Kavita Rao",
        "email": "kavita.rao@company.com",
        "department": "Engineering",
    }
    response = await async_client.post("/api/v1/employees", json=new_emp_payload)
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_employees(async_client: AsyncClient, auth_headers: dict[str, str]):
    now = datetime.now(UTC)
    mock_items = [
        {
            "employee_id": "EMP-001",
            "name": "Aarav Sharma",
            "email": "aarav@company.com",
            "department": "Engineering",
            "role": "Engineer",
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
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
            "app.repositories.employee_repo.EmployeeRepository.list_employees",
            new_callable=AsyncMock,
        ) as mock_list,
    ):
        mock_admin_find.return_value = mock_admin
        mock_list.return_value = (mock_items, 1)

        response = await async_client.get(
            "/api/v1/employees?page=1&page_size=20", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["employee_id"] == "EMP-001"


@pytest.mark.asyncio
async def test_get_employee_not_found(async_client: AsyncClient, auth_headers: dict[str, str]):
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
            "app.repositories.employee_repo.EmployeeRepository.find_by_id", new_callable=AsyncMock
        ) as mock_find,
    ):
        mock_admin_find.return_value = mock_admin
        mock_find.return_value = None

        response = await async_client.get("/api/v1/employees/EMP-NONEXISTENT", headers=auth_headers)
        assert response.status_code == 404
