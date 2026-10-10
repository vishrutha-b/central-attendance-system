"""
Unit tests for security components (Argon2 password hashing and JWT token handling).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import get_settings
from app.exceptions import InvalidTokenError, TokenExpiredError
from app.security.auth import create_access_token, decode_access_token
from app.security.password import hash_password, verify_password


def test_password_hashing_and_verification():
    plain = "SuperSecretPassword123!"
    hashed = hash_password(plain)

    assert hashed != plain
    assert hashed.startswith("$argon2")
    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_create_and_decode():
    payload = {"sub": "ADM-001", "role": "admin", "username": "adminuser"}
    token, expires_in = create_access_token(payload)

    assert isinstance(token, str)
    assert expires_in > 0

    decoded = decode_access_token(token)
    assert decoded["sub"] == "ADM-001"
    assert decoded["role"] == "admin"
    assert decoded["username"] == "adminuser"
    assert "exp" in decoded


def test_jwt_expired_token():
    settings = get_settings()
    now = datetime.now(tz=UTC)
    expired_payload = {
        "sub": "ADM-001",
        "role": "admin",
        "iat": now - timedelta(hours=2),
        "exp": now - timedelta(hours=1),
    }
    expired_token = jwt.encode(
        expired_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )

    with pytest.raises(TokenExpiredError):
        decode_access_token(expired_token)


def test_jwt_invalid_signature():
    settings = get_settings()
    now = datetime.now(tz=UTC)
    payload = {
        "sub": "ADM-001",
        "role": "admin",
        "iat": now,
        "exp": now + timedelta(hours=1),
    }
    bad_signature_token = jwt.encode(
        payload, "different_secret_key_that_does_not_match!", algorithm=settings.jwt_algorithm
    )

    with pytest.raises(InvalidTokenError):
        decode_access_token(bad_signature_token)
