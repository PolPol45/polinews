"""
Rewards and social router — GET /balance, POST /comment.
"""
from __future__ import annotations

import hashlib
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from polinews.api.auth import get_current_user
from polinews.config import DB_PATH
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

router = APIRouter(tags=["rewards"])

COMMENT_BONUS = 5
COMMENT_MIN_LEN = 50
COMMENT_MAX_LEN = 1_000
DAILY_CAP = 50


# ── Pydantic models ───────────────────────────────────────────────────────────

class LedgerEntry(BaseModel):
    entry_id: str
    delta_credits: int
    reason: str
    story_id: str | None
    created_at: str


class BalanceResponse(BaseModel):
    current_balance: int
    pending_balance: int
    credits_earned_today: int
    daily_cap: int
    recent_transactions: list[LedgerEntry]


class CommentRequest(BaseModel):
    story_id: str
    text: str


class CommentResponse(BaseModel):
    accepted: bool
    review_status: str
    credits_provisional: int
    comment_id: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    from datetime import date
    return date.today().isoformat()


def _conn() -> sqlite3.Connection:
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    return conn


def _get_balance(conn: sqlite3.Connection, user_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(delta_credits), 0) FROM rewards_ledger WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _get_credits_earned_today(conn: sqlite3.Connection, user_id: str) -> int:
    today = _today_utc()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(delta_credits), 0) FROM rewards_ledger
        WHERE user_id = ? AND delta_credits > 0 AND DATE(created_at) = ?
        """,
        (user_id, today),
    ).fetchone()
    return int(row[0]) if row else 0


def _get_pending_balance(conn: sqlite3.Connection, user_id: str) -> int:
    """Pending = sum of provisional comment bonuses not yet confirmed."""
    row = conn.execute(
        """
        SELECT COALESCE(SUM(r.delta_credits), 0) FROM rewards_ledger r
        JOIN comments c ON r.reference_id = c.comment_id
        WHERE r.user_id = ? AND r.reason = 'comment_bonus' AND c.status = 'pending_review'
        """,
        (user_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _text_fingerprint(text: str) -> str:
    """MinHash-like simple fingerprint: SHA1 of sorted words."""
    words = sorted(set(text.lower().split()))
    return hashlib.sha1(" ".join(words[:30]).encode()).hexdigest()


def _is_duplicate_comment(conn: sqlite3.Connection, story_id: str, text: str, threshold: float = 0.8) -> bool:
    """Check if a very similar comment already exists for this story."""
    new_fp = _text_fingerprint(text)
    rows = conn.execute(
        "SELECT text FROM comments WHERE story_id = ? LIMIT 50",
        (story_id,),
    ).fetchall()
    for r in rows:
        existing_fp = _text_fingerprint(str(r["text"]))
        # Jaccard on fingerprint bytes as a rough proxy
        a_chars = set(new_fp)
        b_chars = set(existing_fp)
        if len(a_chars | b_chars) == 0:
            continue
        sim = len(a_chars & b_chars) / len(a_chars | b_chars)
        if sim >= threshold:
            return True
    return False


# ── GET /balance ──────────────────────────────────────────────────────────────

@router.get("/balance", response_model=BalanceResponse)
def get_balance(
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
) -> BalanceResponse:
    """Return current balance and recent transaction history."""
    user_id = current_user["user_id"]
    conn = _conn()
    try:
        balance = _get_balance(conn, user_id)
        pending = _get_pending_balance(conn, user_id)
        earned_today = _get_credits_earned_today(conn, user_id)

        rows = conn.execute(
            """
            SELECT entry_id, delta_credits, reason, story_id, created_at
            FROM rewards_ledger
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 20
            """,
            (user_id,),
        ).fetchall()
        transactions = [
            LedgerEntry(
                entry_id=str(r["entry_id"]),
                delta_credits=int(r["delta_credits"]),
                reason=str(r["reason"]),
                story_id=str(r["story_id"]) if r["story_id"] else None,
                created_at=str(r["created_at"]),
            )
            for r in rows
        ]
    finally:
        conn.close()

    return BalanceResponse(
        current_balance=balance,
        pending_balance=pending,
        credits_earned_today=earned_today,
        daily_cap=DAILY_CAP,
        recent_transactions=transactions,
    )


# ── POST /comment ─────────────────────────────────────────────────────────────

@router.post("/comment", response_model=CommentResponse)
def post_comment(
    body: CommentRequest,
    current_user: Annotated[dict[str, str], Depends(get_current_user)],
) -> CommentResponse:
    """
    Submit a comment for a story.
    Validates length, deduplication, and rate limits.
    Awards provisional bonus credits (pending_review).
    """
    user_id = current_user["user_id"]
    text = body.text.strip()

    # Length validation
    if len(text) < COMMENT_MIN_LEN:
        raise HTTPException(status_code=400, detail=f"comment_too_short (min {COMMENT_MIN_LEN} chars)")
    if len(text) > COMMENT_MAX_LEN:
        raise HTTPException(status_code=400, detail=f"comment_too_long (max {COMMENT_MAX_LEN} chars)")

    conn = _conn()
    try:
        # Story must be publishable
        story_row = conn.execute(
            "SELECT story_id, status FROM stories WHERE story_id = ? LIMIT 1",
            (body.story_id,),
        ).fetchone()
        if story_row is None:
            raise HTTPException(status_code=404, detail="story_not_found")
        if story_row["status"] != "publishable":
            raise HTTPException(status_code=409, detail="story_not_publishable")

        # One comment per user per story
        existing = conn.execute(
            "SELECT comment_id FROM comments WHERE user_id = ? AND story_id = ? LIMIT 1",
            (user_id, body.story_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="comment_already_submitted")

        # Similarity dedup
        if _is_duplicate_comment(conn, body.story_id, text):
            raise HTTPException(status_code=409, detail="comment_too_similar_to_existing")

        comment_id = str(uuid.uuid4())
        now = _utc_now()

        conn.execute(
            """
            INSERT INTO comments (comment_id, user_id, story_id, text, status, created_at)
            VALUES (?, ?, ?, ?, 'pending_review', ?)
            """,
            (comment_id, user_id, body.story_id, text, now),
        )

        # Emit provisional bonus (pending_review — tracked via comment status)
        earned_today = _get_credits_earned_today(conn, user_id)
        credits_provisional = min(COMMENT_BONUS, max(0, DAILY_CAP - earned_today))

        if credits_provisional > 0:
            conn.execute(
                """
                INSERT INTO rewards_ledger
                  (entry_id, user_id, story_id, delta_credits, reason, reference_id, created_at)
                VALUES (?, ?, ?, ?, 'comment_bonus', ?, ?)
                """,
                (str(uuid.uuid4()), user_id, body.story_id,
                 credits_provisional, comment_id, now),
            )

        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    return CommentResponse(
        accepted=True,
        review_status="pending_review",
        credits_provisional=credits_provisional,
        comment_id=comment_id,
    )
