"""Async MongoDB connection lifecycle management."""

from __future__ import annotations

import logging
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from app.config import get_settings

logger = logging.getLogger(__name__)

# Module-level client and database references
_client: AsyncMongoClient | None = None  # type: ignore[type-arg]
_db: Any = None


async def connect_to_database() -> None:
    """Initialize AsyncMongoClient and verify connectivity."""
    global _client, _db
    settings = get_settings()

    logger.info("Connecting to MongoDB at %s", settings.mongodb_uri)
    _client = AsyncMongoClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
    )

    db_name = (
        settings.mongodb_test_db_name if settings.app_env == "testing" else settings.mongodb_db_name
    )
    _db = _client[db_name]

    try:
        await _client.admin.command("ping")
        logger.info("MongoDB connected. Database: %s", db_name)
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        logger.error("MongoDB connection failed: %s", exc)
        raise


async def close_database_connection() -> None:
    """Gracefully close the MongoDB client."""
    global _client, _db
    if _client is not None:
        import inspect

        res = _client.close()
        if inspect.isawaitable(res):
            await res
        _client = None
        _db = None
        logger.info("MongoDB connection closed.")


def get_database() -> Any:
    """Return the active database handle. Raises if not connected."""
    if _db is None:
        raise RuntimeError("Database is not connected. Call connect_to_database() first.")
    return _db


def get_client() -> AsyncMongoClient:  # type: ignore[type-arg]
    """Return the active AsyncMongoClient."""
    if _client is None:
        raise RuntimeError("Database client is not initialized.")
    return _client
