"""Password hashing using pwdlib with Argon2."""

from __future__ import annotations

from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

_password_hash = PasswordHash([Argon2Hasher()])


def hash_password(plain: str) -> str:
    """Return an Argon2 hash of the plaintext password."""
    return _password_hash.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if the plaintext matches the hash."""
    return _password_hash.verify(plain, hashed)
