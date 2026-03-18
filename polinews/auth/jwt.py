"""JWT utilities — sign and verify tokens."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from polinews.config import JWT_ALGORITHM, JWT_EXPIRE_DAYS, JWT_SECRET_KEY

_ISSUER = "polinews"


def create_token(user_id: str, email: str) -> str:
    """Create a signed JWT for an authenticated user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iss": _ISSUER,
        "iat": now,
        "exp": now + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, str]:
    """
    Decode and validate a JWT.

    Returns dict with ``sub`` (user_id) and ``email`` on success.
    Raises ``JWTError`` on invalid / expired token.
    """
    payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], options={"require": ["sub", "email", "exp"]})
    return {"user_id": str(payload["sub"]), "email": str(payload["email"])}
