"""JWT token creation and validation."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.config import get_settings
from app.exceptions import InvalidTokenError, TokenExpiredError

logger = logging.getLogger(__name__)


def create_access_token(payload: dict[str, Any]) -> tuple[str, int]:
    """
    Create a signed JWT access token.

    Returns (token_str, expires_in_seconds).
    """
    settings = get_settings()
    now = datetime.now(tz=UTC)
    expire = now + timedelta(minutes=settings.jwt_expiry_minutes)

    data = payload.copy()
    data.update({"exp": expire, "iat": now})

    token = jwt.encode(data, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, settings.jwt_expiry_minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT. Raises TokenExpiredError or InvalidTokenError on failure.
    Never logs the token itself.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        return payload  # type: ignore[return-value]
    except jwt.ExpiredSignatureError:
        raise TokenExpiredError() from None
    except jwt.InvalidTokenError as exc:
        logger.warning("JWT validation failed: %s", type(exc).__name__)
        raise InvalidTokenError() from exc
