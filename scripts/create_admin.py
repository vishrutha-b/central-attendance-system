"""
CLI script to create or verify the initial admin account in MongoDB.
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
from app.security.password import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("create_admin")


async def create_admin(
    username: str | None = None, email: str | None = None, password: str | None = None
) -> None:
    settings = get_settings()
    username = username or settings.initial_admin_username
    email = email or settings.initial_admin_email
    password = password or settings.initial_admin_password

    await connect_to_database()
    db = get_database()
    await create_indexes(db)

    admin_repo = AdminRepository(db)

    existing = await admin_repo.find_by_username(username)
    if existing:
        logger.info(
            "Admin user '%s' already exists (admin_id=%s). No change made.",
            username,
            existing.get("admin_id"),
        )
        await close_database_connection()
        return

    admin_doc = {
        "admin_id": str(uuid.uuid4()),
        "username": username,
        "email": email,
        "hashed_password": hash_password(password),
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(UTC),
    }

    await admin_repo.create(admin_doc)
    logger.info("Admin user '%s' created successfully (email: %s).", username, email)
    await close_database_connection()


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or verify CAMS initial admin user.")
    parser.add_argument("--username", help="Admin username (default: from .env)")
    parser.add_argument("--email", help="Admin email (default: from .env)")
    parser.add_argument("--password", help="Admin password (default: from .env)")
    args = parser.parse_args()

    asyncio.run(create_admin(args.username, args.email, args.password))


if __name__ == "__main__":
    main()
