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
    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_username", new_callable=AsyncMock
        ) as mock_find,
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_email", new_callable=AsyncMock
        ) as mock_email_find,
        patch(
            "app.repositories.admin_repo.AdminRepository.find_super_admin", new_callable=AsyncMock
        ) as mock_super_find,
        patch(
            "app.repositories.employee_repo.EmployeeRepository.find_by_id", new_callable=AsyncMock
        ) as mock_emp_find,
        patch(
            "app.repositories.employee_repo.EmployeeRepository.find_by_email",
            new_callable=AsyncMock,
        ) as mock_emp_email_find,
    ):
        mock_find.return_value = None
        mock_email_find.return_value = None
        mock_super_find.return_value = None
        mock_emp_find.return_value = None
        mock_emp_email_find.return_value = None

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "unknown", "password": "Password123!"},
        )
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_super_admin_success(async_client: AsyncClient):
    mock_super_admin = {
        "admin_id": "ADM-SUPER-001",
        "username": "vishrutha",
        "email": "vishrutha7104@gmail.com",
        "hashed_password": hash_password("Vishu@2004"),
        "role": "super_admin",
        "is_active": True,
        "tenant_id": "default",
    }

    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_username", new_callable=AsyncMock
        ) as mock_u_find,
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_email", new_callable=AsyncMock
        ) as mock_e_find,
        patch(
            "app.repositories.admin_repo.AdminRepository.find_super_admin", new_callable=AsyncMock
        ) as mock_s_find,
    ):
        mock_u_find.return_value = None
        mock_e_find.return_value = None
        mock_s_find.return_value = mock_super_admin

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "vishrutha", "password": "Vishu@2004"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


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


@pytest.mark.asyncio
async def test_forgot_password_admin_success(async_client: AsyncClient):
    mock_admin = {
        "admin_id": "ADM-001",
        "username": "adminuser",
        "email": "admin@tenant1.com",
        "name": "Tenant Administrator",
        "role": "admin",
        "is_active": True,
    }

    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_email",
            new_callable=AsyncMock,
            return_value=mock_admin,
        ),
        patch(
            "app.repositories.password_reset_repo.PasswordResetRepository.create_reset_token",
            new_callable=AsyncMock,
            return_value="token-id-123",
        ),
        patch(
            "app.services.notification_service.NotificationService.send_password_reset_email",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "admin@tenant1.com", "tenant_id": "tenant-1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "Verification code sent" in data["message"]
        assert data["tenant_id"] == "tenant-1"


@pytest.mark.asyncio
async def test_forgot_password_not_found_returns_generic_message(async_client: AsyncClient):
    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_email",
            new_callable=AsyncMock,
            return_value=None,
        ),
        patch(
            "app.repositories.employee_repo.EmployeeRepository.find_by_email",
            new_callable=AsyncMock,
            return_value=None,
        ),
    ):
        response = await async_client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@company.com", "tenant_id": "tenant-1"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "If an account exists with that email" in data["message"]


@pytest.mark.asyncio
async def test_verify_reset_code_success(async_client: AsyncClient):
    valid_token = {
        "email": "user@example.com",
        "code": "123456",
        "user_type": "employee",
        "user_id": "EMP-001",
        "is_used": False,
    }

    with patch(
        "app.repositories.password_reset_repo.PasswordResetRepository.find_valid_token",
        new_callable=AsyncMock,
        return_value=valid_token,
    ):
        response = await async_client.post(
            "/api/v1/auth/verify-reset-code",
            json={"email": "user@example.com", "code": "123456", "tenant_id": "tenant-1"},
        )
        assert response.status_code == 200
        assert response.json()["valid"] is True


@pytest.mark.asyncio
async def test_verify_reset_code_invalid(async_client: AsyncClient):
    with patch(
        "app.repositories.password_reset_repo.PasswordResetRepository.find_valid_token",
        new_callable=AsyncMock,
        return_value=None,
    ):
        response = await async_client.post(
            "/api/v1/auth/verify-reset-code",
            json={"email": "user@example.com", "code": "000000", "tenant_id": "tenant-1"},
        )
        assert response.status_code == 400
        assert "Invalid or expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_reset_password_success(async_client: AsyncClient):
    valid_token = {
        "email": "user@example.com",
        "code": "123456",
        "user_type": "admin",
        "user_id": "ADM-001",
        "is_used": False,
    }

    with (
        patch(
            "app.repositories.password_reset_repo.PasswordResetRepository.find_valid_token",
            new_callable=AsyncMock,
            return_value=valid_token,
        ),
        patch(
            "app.repositories.admin_repo.AdminRepository.update_password",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch(
            "app.repositories.password_reset_repo.PasswordResetRepository.mark_used",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        response = await async_client.post(
            "/api/v1/auth/reset-password",
            json={
                "email": "user@example.com",
                "code": "123456",
                "new_password": "NewStrongPassword123!",
                "tenant_id": "tenant-1",
            },
        )
        assert response.status_code == 200
        assert "Password successfully reset" in response.json()["message"]

