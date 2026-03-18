"""
Reading sessions tracking API.
Used by the frontend to report engagement metrics (active time, scroll depth).
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from polinews.api.auth import get_optional_user
from polinews.config import DB_PATH
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    story_id: str
    device_type: str | None = None
    locale: str | None = "all"


class SessionCreateResponse(BaseModel):
    session_id: str


class SessionUpdateRequest(BaseModel):
    active_seconds: int | None = None
    scroll_depth: int | None = None
    total_seconds: int | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _conn() -> sqlite3.Connection:
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    return conn


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("", response_model=SessionCreateResponse)
def create_session(
    body: SessionCreateRequest,
    current_user: Annotated[dict[str, str] | None, Depends(get_optional_user)] = None,
) -> SessionCreateResponse:
    """
    Open a new reading session for a story.
    Returns a session_id to be used for subsequent updates.
    """
    user_id = current_user["user_id"] if current_user else "anonymous"
    session_id = str(uuid.uuid4())
    
    conn = _conn()
    try:
        # Verify story exists
        story = conn.execute("SELECT topic_slug FROM stories WHERE story_id = ?", (body.story_id,)).fetchone()
        if not story:
            raise HTTPException(status_code=404, detail="story_not_found")
            
        conn.execute(
            """
            INSERT INTO reading_sessions 
            (session_id, user_id, story_id, topic_slug, started_at, device_type, locale)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, user_id, body.story_id, story["topic_slug"], _utc_now(), body.device_type, body.locale)
        )
        conn.commit()
    finally:
        conn.close()
        
    return SessionCreateResponse(session_id=session_id)


@router.patch("/{session_id}")
def update_session(session_id: str, body: SessionUpdateRequest) -> dict[str, str]:
    """
    Update an existing session with engagement metrics.
    """
    conn = _conn()
    try:
        # Build dynamic update
        updates = []
        params: list[Any] = []
        if body.active_seconds is not None:
            updates.append("active_seconds = ?")
            params.append(body.active_seconds)
        if body.scroll_depth is not None:
            updates.append("scroll_depth = ?")
            params.append(body.scroll_depth)
        if body.total_seconds is not None:
            updates.append("total_seconds = ?")
            params.append(body.total_seconds)
            
        if not updates:
            return {"status": "no_change"}
            
        params.append(session_id)
        query = f"UPDATE reading_sessions SET {', '.join(updates)} WHERE session_id = ?"
        
        cur = conn.execute(query, params)
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="session_not_found")
        conn.commit()
    finally:
        conn.close()
        
    return {"status": "updated"}
