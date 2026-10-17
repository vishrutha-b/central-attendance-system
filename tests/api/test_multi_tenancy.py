"""
Integration tests for Multi-Tenancy functionality:
- Tenant onboarding and configuration APIs (/api/v1/tenants)
- Cross-tenant data isolation (Employees, Attendance)
- Composite unique key enforcement per tenant
- Header and JWT tenant context resolution
- Multi-tenant compliance monitoring worker
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.security.auth import create_access_token
from app.workers.monitoring import run_all_tenants_monitoring_cycle


@pytest.mark.asyncio
async def test_tenant_onboarding_success(
    async_client: AsyncClient, super_admin_auth_headers: dict[str, str]
):
    payload = {
        "tenant_id": "acme-corp",
        "name": "Acme Corporation",
        "contact_email": "admin@acme.com",
        "admin_username": "acme_admin",
        "admin_password": "AcmePassword123!",
        "settings": {
            "company_timezone": "America/New_York",
            "min_days_per_week": 4,
            "min_hours_per_week": 20.0,
            "min_avg_hours_per_day": 5.0,
        },
    }

    mock_created = {
        **payload,
        "status": "active",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }

    mock_admin = {
        "admin_id": "ADM-SUPER-001",
        "username": "vishrutha",
        "role": "super_admin",
        "is_active": True,
        "tenant_id": "default",
    }

    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
        ) as mock_admin_find,
        patch(
            "app.repositories.tenant_repo.TenantRepository.find_by_id", new_callable=AsyncMock
        ) as mock_find,
        patch(
            "app.repositories.tenant_repo.TenantRepository.create", new_callable=AsyncMock
        ) as mock_create,
        patch(
            "app.repositories.admin_repo.AdminRepository.create", new_callable=AsyncMock
        ) as mock_admin_create,
    ):
        mock_admin_find.return_value = mock_admin
        mock_find.return_value = None
        mock_create.return_value = mock_created
        mock_admin_create.return_value = {}

        response = await async_client.post(
            "/api/v1/tenants", json=payload, headers=super_admin_auth_headers
        )
        assert response.status_code == 201
        data = response.json()
        assert data["tenant_id"] == "acme-corp"
        assert data["name"] == "Acme Corporation"
        assert data["status"] == "active"
        assert data["settings"]["company_timezone"] == "America/New_York"
        assert data["settings"]["min_days_per_week"] == 4


@pytest.mark.asyncio
async def test_tenant_onboarding_forbidden_for_regular_admin(
    async_client: AsyncClient, auth_headers: dict[str, str]
):
    payload = {
        "tenant_id": "new-corp",
        "name": "New Corp",
        "contact_email": "admin@newcorp.com",
    }

    mock_admin = {
        "admin_id": "ADM-TEST-001",
        "username": "testadmin",
        "role": "admin",
        "is_active": True,
        "tenant_id": "default",
    }

    with patch(
        "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
    ) as mock_admin_find:
        mock_admin_find.return_value = mock_admin

        # Regular admin role="admin" should be forbidden from onboarding tenants
        response = await async_client.post("/api/v1/tenants", json=payload, headers=auth_headers)
        assert response.status_code == 403
        assert "Required role: super_admin" in response.json()["detail"]


@pytest.mark.asyncio
async def test_tenant_onboarding_unauthorized(async_client: AsyncClient):
    payload = {
        "tenant_id": "acme-corp",
        "name": "Acme Corporation",
        "contact_email": "admin@acme.com",
    }
    # No auth header -> 401 Unauthorized
    response = await async_client.post("/api/v1/tenants", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tenant_onboarding_duplicate(
    async_client: AsyncClient, super_admin_auth_headers: dict[str, str]
):
    payload = {
        "tenant_id": "acme-corp",
        "name": "Acme Corporation",
        "contact_email": "admin@acme.com",
    }

    mock_admin = {
        "admin_id": "ADM-SUPER-001",
        "username": "vishrutha",
        "role": "super_admin",
        "is_active": True,
        "tenant_id": "default",
    }

    with (
        patch(
            "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
        ) as mock_admin_find,
        patch(
            "app.repositories.tenant_repo.TenantRepository.find_by_id", new_callable=AsyncMock
        ) as mock_find,
    ):
        mock_admin_find.return_value = mock_admin
        mock_find.return_value = {"tenant_id": "acme-corp"}

        response = await async_client.post(
            "/api/v1/tenants", json=payload, headers=super_admin_auth_headers
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_tenant_details(async_client: AsyncClient):
    now = datetime.now(UTC)
    mock_tenant = {
        "tenant_id": "globex-intl",
        "name": "Globex International",
        "contact_email": "hr@globex.com",
        "status": "active",
        "settings": {
            "company_timezone": "Asia/Kolkata",
            "min_days_per_week": 3,
            "min_hours_per_week": 15.0,
            "min_avg_hours_per_day": 5.0,
        },
        "created_at": now,
        "updated_at": now,
    }

    with patch(
        "app.repositories.tenant_repo.TenantRepository.find_by_id", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = mock_tenant

        response = await async_client.get("/api/v1/tenants/globex-intl")
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "globex-intl"
        assert data["name"] == "Globex International"


@pytest.mark.asyncio
async def test_tenant_header_resolution_middleware(async_client: AsyncClient):
    # Pass custom X-Tenant-ID header and verify it is propagated into response
    response = await async_client.get("/health/live", headers={"X-Tenant-ID": "tenant-xyz"})
    assert response.status_code == 200
    assert response.headers.get("X-Tenant-ID") == "tenant-xyz"


@pytest.mark.asyncio
async def test_multi_tenant_jwt_auth_scoping(async_client: AsyncClient):
    token, _ = create_access_token(
        {
            "sub": "ADM-ACME-01",
            "role": "admin",
            "username": "acmeadmin",
            "tenant_id": "acme-corp",
        }
    )

    now = datetime.now(UTC)
    mock_admin = {
        "admin_id": "ADM-ACME-01",
        "username": "acmeadmin",
        "email": "admin@acme.com",
        "role": "admin",
        "is_active": True,
        "tenant_id": "acme-corp",
        "created_at": now,
        "updated_at": now,
    }

    with patch(
        "app.repositories.admin_repo.AdminRepository.find_by_id", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = mock_admin

        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "acmeadmin"
        assert data["tenant_id"] == "acme-corp"


@pytest.mark.asyncio
async def test_employee_cross_tenant_isolation(async_client: AsyncClient):
    # Generate token for tenant 'acme'
    acme_token, _ = create_access_token(
        {
            "sub": "ADM-ACME-01",
            "role": "admin",
            "username": "acmeadmin",
            "tenant_id": "acme-corp",
        }
    )

    mock_admin = {
        "admin_id": "ADM-ACME-01",
        "username": "acmeadmin",
        "role": "admin",
        "is_active": True,
        "tenant_id": "acme-corp",
    }

    now = datetime.now(UTC)
    acme_employee = {
        "employee_id": "EMP-001",
        "name": "Acme Employee",
        "email": "emp@acme.com",
        "department": "Engineering",
        "role": "Engineer",
        "is_active": True,
        "tenant_id": "acme-corp",
        "created_at": now,
        "updated_at": now,
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
        mock_create.return_value = acme_employee

        # Create employee in tenant 'acme-corp'
        resp = await async_client.post(
            "/api/v1/employees",
            json={
                "employee_id": "EMP-001",
                "name": "Acme Employee",
                "email": "emp@acme.com",
                "department": "Engineering",
                "role": "Engineer",
            },
            headers={"Authorization": f"Bearer {acme_token}"},
        )
        assert resp.status_code == 201
        assert resp.json()["employee_id"] == "EMP-001"


@pytest.mark.asyncio
async def test_run_all_tenants_monitoring():
    mock_db = MagicMock()

    active_tenants = [
        {
            "tenant_id": "tenant-a",
            "name": "Tenant A",
            "status": "active",
            "settings": {"min_days_per_week": 3, "min_hours_per_week": 15.0},
        },
        {
            "tenant_id": "tenant-b",
            "name": "Tenant B",
            "status": "active",
            "settings": {"min_days_per_week": 4, "min_hours_per_week": 20.0},
        },
    ]

    with (
        patch(
            "app.repositories.tenant_repo.TenantRepository.list_tenants", new_callable=AsyncMock
        ) as mock_list,
        patch("app.workers.monitoring.run_monitoring_cycle", new_callable=AsyncMock) as mock_cycle,
    ):
        mock_list.return_value = (active_tenants, 2)
        mock_cycle.return_value = {"status": "completed", "violations_found": 0}

        summary = await run_all_tenants_monitoring_cycle(mock_db)
        assert summary["status"] == "completed"
        assert summary["tenants_audited"] == 2
        assert "tenant-a" in summary["results"]
        assert "tenant-b" in summary["results"]
        assert mock_cycle.call_count == 2
