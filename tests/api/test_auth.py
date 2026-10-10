"""
Tests for authentication endpoints (/api/v1/auth).
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.security.password import hash_password


@pytest.mark.asyncio
async def test_login_success(async_client: AsyncClient):
    mock_admin = {
        "admin_id": "ADM-001",
        "username": "testadmin",
        "email": "testadmin@company.com",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    with patch(
        "app.repositories.admin_repo.AdminRepository.find_by_username", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = mock_admin

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "ValidPassword123!"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient):
    mock_admin = {
        "admin_id": "ADM-001",
        "username": "testadmin",
        "email": "testadmin@company.com",
        "hashed_password": hash_password("ValidPassword123!"),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    with patch(
        "app.repositories.admin_repo.AdminRepository.find_by_username", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = mock_admin

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "testadmin", "password": "WrongPassword!"},
        )
        assert response.status_code == 401
        assert "Invalid username or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_user_not_found(async_client: AsyncClient):
    with patch(
        "app.repositories.admin_repo.AdminRepository.find_by_username", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "unknown", "password": "Password123!"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_unauthorized(async_client: AsyncClient):
    response = await async_client.get("/api/v1/auth/me")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_get_me_authorized(async_client: AsyncClient, auth_headers: dict[str, str]):
    mock_admin = {
        "admin_id": "ADM-TEST-001",
        "username": "testadmin",
        "email": "testadmin@company.com",
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    with patch(
        "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = mock_admin

        response = await async_client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["admin_id"] == "ADM-TEST-001"
        assert data["username"] == "testadmin"
        assert "hashed_password" not in data
