"""
Publisher dashboard API — GET /publisher-dashboard.
Requires X-Publisher-Key header matching PUBLISHER_API_KEY config.
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from polinews.config import DB_PATH, PUBLISHER_API_KEY
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

router = APIRouter(tags=["publisher"])


# ── Auth guard ────────────────────────────────────────────────────────────────

def _require_publisher_key(request: Request) -> None:
    key = request.headers.get("X-Publisher-Key", "")
    if not key or key != PUBLISHER_API_KEY:
        raise HTTPException(status_code=403, detail="invalid_publisher_key")


# ── Pydantic models ───────────────────────────────────────────────────────────

class FunnelMetrics(BaseModel):
    quiz_started_total: int
    quiz_passed_total: int
    pass_rate: float
    avg_quiz_time_seconds: float | None


class QualityMetrics(BaseModel):
    pass_rate_7d: list[float]
    comment_accept_rate: float


class EconomicsMetrics(BaseModel):
    credits_issued_today: int
    credits_revoked_today: int


class FraudMetrics(BaseModel):
    signals_open: int
    signals_high_severity: int


class ContentMetrics(BaseModel):
    publishable_stories: int
    quiz_available_stories: int
    quiz_coverage_pct: float


class DashboardResponse(BaseModel):
    funnel: FunnelMetrics
    quality: QualityMetrics
    economics: EconomicsMetrics
    fraud: FraudMetrics
    content: ContentMetrics


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    return conn


def _today() -> str:
    return date.today().isoformat()


def _days_ago(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


# ── Endpoint ──────────────────────────────────────────────────────────────────

@router.get("/publisher-dashboard", response_model=DashboardResponse)
def get_publisher_dashboard(request: Request) -> DashboardResponse:
    """Publisher KPI dashboard. Requires X-Publisher-Key header."""
    _require_publisher_key(request)
    conn = _conn()
    try:
        # Funnel
        total_started = conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        total_passed = conn.execute("SELECT COUNT(*) FROM attempts WHERE passed = 1").fetchone()[0]
        pass_rate = (total_passed / total_started) if total_started > 0 else 0.0

        avg_time_row = conn.execute(
            "SELECT AVG(client_elapsed_seconds) FROM attempts WHERE client_elapsed_seconds > 0"
        ).fetchone()
        avg_quiz_time = float(avg_time_row[0]) if avg_time_row and avg_time_row[0] else None

        # 7-day pass rate trend
        pass_rate_7d: list[float] = []
        for days_back in range(6, -1, -1):
            day = (date.today() - timedelta(days=days_back)).isoformat()
            row = conn.execute(
                """
                SELECT
                  COUNT(*) FILTER (WHERE passed = 1) AS p,
                  COUNT(*) AS t
                FROM attempts
                WHERE DATE(created_at) = ?
                """,
                (day,),
            ).fetchone()
            if row and row[1] > 0:
                pass_rate_7d.append(round(row[0] / row[1], 3))
            else:
                pass_rate_7d.append(0.0)

        # Comment accept rate
        total_comments = conn.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
        accepted_comments = conn.execute(
            "SELECT COUNT(*) FROM comments WHERE status = 'accepted'"
        ).fetchone()[0]
        comment_accept_rate = (accepted_comments / total_comments) if total_comments > 0 else 0.0

        # Economics
        today = _today()
        credits_issued = conn.execute(
            """
            SELECT COALESCE(SUM(delta_credits), 0) FROM rewards_ledger
            WHERE delta_credits > 0 AND DATE(created_at) = ?
            """,
            (today,),
        ).fetchone()[0]
        credits_revoked = abs(conn.execute(
            """
            SELECT COALESCE(SUM(delta_credits), 0) FROM rewards_ledger
            WHERE delta_credits < 0 AND DATE(created_at) = ?
            """,
            (today,),
        ).fetchone()[0])

        # Fraud
        signals_open = conn.execute(
            "SELECT COUNT(*) FROM fraud_signals WHERE resolved_at IS NULL"
        ).fetchone()[0]
        signals_high = conn.execute(
            "SELECT COUNT(*) FROM fraud_signals WHERE resolved_at IS NULL AND severity IN ('high', 'critical')"
        ).fetchone()[0]

        # Content
        publishable = conn.execute(
            "SELECT COUNT(*) FROM stories WHERE status = 'publishable'"
        ).fetchone()[0]
        quiz_available = conn.execute(
            "SELECT COUNT(*) FROM stories WHERE status = 'publishable' AND quiz_status = 'quiz_available'"
        ).fetchone()[0]
        coverage = (quiz_available / publishable * 100) if publishable > 0 else 0.0

    finally:
        conn.close()

    return DashboardResponse(
        funnel=FunnelMetrics(
            quiz_started_total=int(total_started),
            quiz_passed_total=int(total_passed),
            pass_rate=round(pass_rate, 3),
            avg_quiz_time_seconds=round(avg_quiz_time, 1) if avg_quiz_time else None,
        ),
        quality=QualityMetrics(
            pass_rate_7d=pass_rate_7d,
            comment_accept_rate=round(comment_accept_rate, 3),
        ),
        economics=EconomicsMetrics(
            credits_issued_today=int(credits_issued),
            credits_revoked_today=int(credits_revoked),
        ),
        fraud=FraudMetrics(
            signals_open=int(signals_open),
            signals_high_severity=int(signals_high),
        ),
        content=ContentMetrics(
            publishable_stories=int(publishable),
            quiz_available_stories=int(quiz_available),
            quiz_coverage_pct=round(coverage, 1),
        ),
    )
