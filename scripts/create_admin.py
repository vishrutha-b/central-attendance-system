"""
CLI script to create or verify the initial admin account in MongoDB with multi-tenancy.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import get_settings
from app.database.connection import close_database_connection, connect_to_database, get_database
from app.database.indexes import create_indexes
from app.repositories.admin_repo import AdminRepository
from app.repositories.tenant_repo import TenantRepository
from app.security.password import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("create_admin")


async def create_admin(
    username: str | None = None,
    email: str | None = None,
    password: str | None = None,
    tenant_id: str = "default",
) -> None:
    settings = get_settings()
    username = username or settings.initial_admin_username
    email = email or settings.initial_admin_email
    password = password or settings.initial_admin_password

    await connect_to_database()
    db = get_database()
    await create_indexes(db)

    # Ensure tenant exists
    tenant_repo = TenantRepository(db)
    if tenant_id == "default":
        await tenant_repo.ensure_default_tenant()
    else:
        existing_tenant = await tenant_repo.find_by_id(tenant_id)
        if not existing_tenant:
            await tenant_repo.create(
                {
                    "tenant_id": tenant_id,
                    "name": f"{tenant_id.title()} Org",
                    "contact_email": email,
                    "status": "active",
                    "settings": {},
                }
            )

    admin_repo = AdminRepository(db, tenant_id=tenant_id)

    existing = await admin_repo.find_by_username(username)
    if existing:
        logger.info(
            "Admin user '%s' already exists for tenant '%s' (admin_id=%s). No change made.",
            username,
            tenant_id,
            existing.get("admin_id"),
        )
        await close_database_connection()
        return

    # Only vishrutha can be super_admin
    role = "super_admin" if username == "vishrutha" else "admin"

    admin_doc = {
        "tenant_id": tenant_id,
        "admin_id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "name": "Vishrutha (Super Admin)" if username == "vishrutha" else f"{username} Admin",
        "hashed_password": hash_password(password),
        "role": role,
        "is_active": True,
        "created_at": datetime.now(UTC),
    }

    await admin_repo.create(admin_doc)
    logger.info(
        "Admin user '%s' created successfully for tenant '%s' (email: %s).",
        username,
        tenant_id,
        email,
    )
    await close_database_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or verify CAMS initial admin user.")
    parser.add_argument("--username", help="Admin username (default: from .env)")
    parser.add_argument("--email", help="Admin email (default: from .env)")
    parser.add_argument("--password", help="Admin password (default: from .env)")
    parser.add_argument("--tenant-id", default="default", help="Tenant ID (default: 'default')")
    args = parser.parse_args()

    asyncio.run(create_admin(args.username, args.email, args.password, args.tenant_id))


if __name__ == "__main__":
    main()
