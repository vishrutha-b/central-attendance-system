"""
Pytest configuration and shared test fixtures for CAMS.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.config import Settings
from app.database.connection import get_database
from app.main import app
from app.security.auth import create_access_token


@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """Return test settings with safe test configuration."""
    return Settings(
        app_env="testing",
        mongodb_uri="mongodb://localhost:27017",
        mongodb_db_name="cams_test",
        mongodb_test_db_name="cams_test",
        jwt_secret="test_secret_key_at_least_32_characters_long_for_security",
        initial_admin_username="testadmin",
        initial_admin_email="testadmin@company.com",
        initial_admin_password="TestAdminPassword123!",
        email_delivery_mode="disabled",
        company_timezone="Asia/Kolkata",
    )


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Generate valid JWT Authorization header for an admin user."""
    token, _ = create_access_token(
        {"sub": "ADM-TEST-001", "role": "admin", "username": "testadmin"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def super_admin_auth_headers() -> dict[str, str]:
    """Generate valid JWT Authorization header for super admin user."""
    token, _ = create_access_token(
        {"sub": "ADM-SUPER-001", "role": "super_admin", "username": "vishrutha"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def manager_auth_headers() -> dict[str, str]:
    """Generate valid JWT Authorization header for a manager user."""
    token, _ = create_access_token(
        {"sub": "ADM-TEST-002", "role": "manager", "username": "testmanager"}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_db_dependency():
    """Automatically mock database connection dependency."""
    mock_db = MagicMock(name="mock_db")
    app.dependency_overrides[get_database] = lambda: mock_db
    yield mock_db
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous HTTP test client for FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
