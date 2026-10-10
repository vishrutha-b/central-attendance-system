"""Tests for administrator management endpoints (/api/v1/admin)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_admin_user_success(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "username": "sarah_admin",
        "email": "sarah@company.com",
        "password": "SecurePassword123!",
        "role": "admin",
    }

    now = datetime.now(tz=UTC)
    created_doc = {
        "admin_id": "ADM-NEW-001",
        "username": "sarah_admin",
        "email": "sarah@company.com",
        "hashed_password": "hashed_pass_value",
        "role": "admin",
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

    repo_find_id = patch(
        "app.repositories.admin_repo.AdminRepository.find_by_id",
        new_callable=AsyncMock,
    )
    repo_find_user = patch(
        "app.repositories.admin_repo.AdminRepository.find_by_username",
        new_callable=AsyncMock,
    )
    repo_find_email = patch(
        "app.repositories.admin_repo.AdminRepository.find_by_email",
        new_callable=AsyncMock,
    )
    repo_create = patch(
        "app.repositories.admin_repo.AdminRepository.create",
        new_callable=AsyncMock,
    )
    audit_create = patch(
        "app.repositories.admin_repo.AuditRepository.create",
        new_callable=AsyncMock,
    )

    with (
        repo_find_id as mock_find_id,
        repo_find_user as mock_find_user,
        repo_find_email as mock_find_email,
        repo_create as mock_create,
        audit_create,
    ):
        mock_find_id.return_value = mock_admin
        mock_find_user.return_value = None
        mock_find_email.return_value = None
        mock_create.return_value = created_doc

        response = await async_client.post(
            "/api/v1/admin/users",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "sarah_admin"
        assert data["email"] == "sarah@company.com"
        assert data["role"] == "admin"
        assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_create_admin_user_duplicate_username(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
):
    payload = {
        "username": "existing_admin",
        "email": "different@company.com",
        "password": "SecurePassword123!",
        "role": "admin",
    }

    mock_admin = {
        "admin_id": "ADM-TEST-001",
        "username": "testadmin",
        "role": "admin",
        "is_active": True,
    }

    repo_find_id = patch(
        "app.repositories.admin_repo.AdminRepository.find_by_id",
        new_callable=AsyncMock,
    )
    repo_find_user = patch(
        "app.repositories.admin_repo.AdminRepository.find_by_username",
        new_callable=AsyncMock,
    )

    with (
        repo_find_id as mock_find_id,
        repo_find_user as mock_find_user,
    ):
        mock_find_id.return_value = mock_admin
        mock_find_user.return_value = {"username": "existing_admin"}

        response = await async_client.post(
            "/api/v1/admin/users",
            json=payload,
            headers=auth_headers,
        )
        assert response.status_code == 409
        assert "already taken" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_list_admin_users(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
):
    now = datetime.now(tz=UTC)
    mock_admins = [
        {
            "admin_id": "ADM-001",
            "username": "admin1",
            "email": "admin1@company.com",
            "role": "admin",
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

    repo_find_id = patch(
        "app.repositories.admin_repo.AdminRepository.find_by_id",
        new_callable=AsyncMock,
    )
    repo_list = patch(
        "app.repositories.admin_repo.AdminRepository.list_admins",
        new_callable=AsyncMock,
    )

    with (
        repo_find_id as mock_find_id,
        repo_list as mock_list,
    ):
        mock_find_id.return_value = mock_admin
        mock_list.return_value = mock_admins

        response = await async_client.get("/api/v1/admin/users", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "admin1"
