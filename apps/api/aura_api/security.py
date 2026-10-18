"""Authentication primitives. Never accept user IDs from request bodies for authorization."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

ISSUER = "aura-date"
AUDIENCE = "aura-date-mobile"
HASHER = PasswordHasher(time_cost=2, memory_cost=65536, parallelism=2)


def signing_secret() -> str:
    secret = os.getenv("AURA_SECRET_KEY", "development-only-unsafe-local-aura-key")
    if os.getenv("AURA_ENV", "development").lower() == "production":
        if len(secret) < 32 or secret == "development-only-unsafe-local-aura-key":
            raise RuntimeError("Production requires a strong unique AURA_SECRET_KEY")
    return secret


def hash_password(password: str) -> str:
    return HASHER.hash(password)


def password_matches(password: str, hashed: str) -> bool:
    try:
        return HASHER.verify(hashed, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def issue_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user_id, "iss": ISSUER, "aud": AUDIENCE,
         "iat": now, "exp": now + timedelta(hours=12)},
        signing_secret(),
        algorithm="HS256",
    )


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token, signing_secret(), algorithms=["HS256"],
            issuer=ISSUER, audience=AUDIENCE, options={"require": ["sub", "exp", "iss", "aud"]}
        )
        user_id = payload["sub"]
        return user_id if isinstance(user_id, str) and user_id else None
    except jwt.PyJWTError:
        return None
