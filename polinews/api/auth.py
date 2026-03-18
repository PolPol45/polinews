"""Auth FastAPI router — magic link + JWT endpoints."""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel, EmailStr

from polinews.auth.jwt import create_token, decode_token
from polinews.auth.magic_link import expiry_iso, generate_token, is_expired, send_magic_link
from polinews.config import DB_PATH
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer(auto_error=False)


# ─── Pydantic models ──────────────────────────────────────────────────────────

class MagicLinkRequest(BaseModel):
    email: EmailStr
    base_url: str = "http://localhost:8000"


class MagicLinkVerify(BaseModel):
    token: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    created_at: str
    reputation: int
    onboarding_state: str


# ─── Dependency: current user ─────────────────────────────────────────────────

def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, str]:
    """
    FastAPI dependency — extracts and validates the Bearer JWT.
    Returns dict with ``user_id`` and ``email``.
    Raises 401 if missing or invalid.
    """
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing_authorization_header")
    try:
        return decode_token(credentials.credentials)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail=f"invalid_token: {exc}") from exc


def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> dict[str, str] | None:
    """Like get_current_user but returns None instead of 401 when unauthenticated."""
    if credentials is None:
        return None
    try:
        return decode_token(credentials.credentials)
    except JWTError:
        return None


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_or_create_user(conn: sqlite3.Connection, email: str) -> str:
    """Return existing user_id or create a new user record. Returns user_id."""
    row = conn.execute(
        "SELECT user_id FROM users WHERE email = ? LIMIT 1", (email,)
    ).fetchone()
    if row:
        return str(row["user_id"])
    user_id = str(uuid.uuid4())
    conn.execute(
        """
        INSERT INTO users (user_id, email, created_at, reputation, onboarding_state)
        VALUES (?, ?, ?, 100, 'new')
        """,
        (user_id, email, _utc_now()),
    )
    return user_id


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/request-magic-link", status_code=202)
def request_magic_link(body: MagicLinkRequest) -> dict[str, str]:
    """
    Issue a one-use magic link token for the given email.
    The link is delivered according to MAGIC_LINK_DELIVERY config
    (stdout in dev, Resend in prod).
    """
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    try:
        user_id = _get_or_create_user(conn, body.email)
        token = generate_token()
        expires_at = expiry_iso()
        conn.execute(
            """
            INSERT INTO magic_link_tokens (token, user_id, email, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (token, user_id, body.email, expires_at),
        )
        conn.commit()
    finally:
        conn.close()

    send_magic_link(body.email, token, base_url=body.base_url)
    return {"status": "sent", "delivery": "check_configured_channel"}


@router.post("/verify", response_model=TokenResponse)
def verify_magic_link(body: MagicLinkVerify) -> TokenResponse:
    """
    Verify a magic link token and return a signed JWT on success.
    The token is consumed (marked used_at) on first successful call.
    """
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    try:
        row = conn.execute(
            "SELECT token, user_id, email, expires_at, used_at FROM magic_link_tokens WHERE token = ?",
            (body.token,),
        ).fetchone()

        if row is None:
            raise HTTPException(status_code=404, detail="token_not_found")
        if row["used_at"] is not None:
            raise HTTPException(status_code=409, detail="token_already_used")
        if is_expired(row["expires_at"]):
            raise HTTPException(status_code=410, detail="token_expired")

        # Mark as used
        conn.execute(
            "UPDATE magic_link_tokens SET used_at = ? WHERE token = ?",
            (_utc_now(), body.token),
        )
        conn.commit()

        user_id = str(row["user_id"])
        email = str(row["email"])
    finally:
        conn.close()

    access_token = create_token(user_id=user_id, email=email)
    return TokenResponse(access_token=access_token, user_id=user_id, email=email)


@router.get("/me", response_model=MeResponse)
def get_me(current_user: Annotated[dict[str, str], Depends(get_current_user)]) -> MeResponse:
    """Return the profile of the currently authenticated user."""
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    try:
        row = conn.execute(
            "SELECT user_id, email, created_at, reputation, onboarding_state FROM users WHERE user_id = ?",
            (current_user["user_id"],),
        ).fetchone()
    finally:
        conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="user_not_found")

    return MeResponse(
        user_id=str(row["user_id"]),
        email=str(row["email"]),
        created_at=str(row["created_at"]),
        reputation=int(row["reputation"]),
        onboarding_state=str(row["onboarding_state"]),
    )
