"""
Analytics API router.
Provides detailed performance metrics for stories and topics to publishers and researchers.
"""
from __future__ import annotations

import sqlite3
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from polinews.config import DB_PATH, PUBLISHER_API_KEY
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ── Auth guard ────────────────────────────────────────────────────────────────

def _require_publisher_key(request: Request) -> None:
    key = request.headers.get("X-Publisher-Key", "")
    if not key or key != PUBLISHER_API_KEY:
        raise HTTPException(status_code=403, detail="invalid_publisher_key")


# ── Pydantic models ───────────────────────────────────────────────────────────

class StoryAnalyticsResponse(BaseModel):
    story_id: str
    comprehension_score: float
    engagement_score: float
    avg_read_seconds: float
    difficulty_index: float
    box_viewed: int
    quiz_started: int
    quiz_passed: int


class TopicTrendItem(BaseModel):
    week_start: str
    attempt_rate: float
    comprehension_score: float
    avg_read_seconds: float
    unique_readers: int


class TopicAnalyticsResponse(BaseModel):
    topic_slug: str
    locale: str
    trends: list[TopicTrendItem]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    return conn


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/story/{story_id}", response_model=StoryAnalyticsResponse)
def get_story_analytics(story_id: str, request: Request) -> StoryAnalyticsResponse:
    """
    Get detailed metrics for a specific story.
    Requires X-Publisher-Key header.
    """
    _require_publisher_key(request)
    conn = _conn()
    try:
        # Get aggregated metrics across all dates for this story
        row = conn.execute("""
            SELECT 
                SUM(box_viewed) as total_views,
                SUM(quiz_started) as total_started,
                SUM(quiz_passed) as total_passed,
                AVG(avg_active_seconds) as avg_seconds,
                AVG(comprehension_score) as avg_comp,
                AVG(engagement_score) as avg_eng
            FROM story_analytics
            WHERE story_id = ?
        """, (story_id,)).fetchone()
        
        if not row or not row["total_views"]:
            # Fallback to calculating from raw data if aggregate doesn't exist yet
            # (or if the job hasn't run today)
            # For simplicity in MVP, we return 404 if no analytics record exists.
            raise HTTPException(status_code=404, detail="analytics_not_found_yet")
            
        # Difficulty index = 1 - pass_rate
        total_started = int(row["total_started"] or 0)
        total_passed = int(row["total_passed"] or 0)
        pass_rate = (total_passed / total_started) if total_started > 0 else 1.0
        
        return StoryAnalyticsResponse(
            story_id=story_id,
            comprehension_score=round(float(row["avg_comp"] or 0.0), 4),
            engagement_score=round(float(row["avg_eng"] or 0.0), 2),
            avg_read_seconds=round(float(row["avg_seconds"] or 0.0), 1),
            difficulty_index=round(1.0 - pass_rate, 2),
            box_viewed=int(row["total_views"]),
            quiz_started=total_started,
            quiz_passed=total_passed
        )
    finally:
        conn.close()


@router.get("/topic/{topic_slug}", response_model=TopicAnalyticsResponse)
def get_topic_analytics(
    topic_slug: str, 
    request: Request,
    locale: str = Query(default="all")
) -> TopicAnalyticsResponse:
    """
    Get weekly trends for a topic.
    Requires X-Publisher-Key header.
    """
    _require_publisher_key(request)
    conn = _conn()
    try:
        rows = conn.execute("""
            SELECT week_start, attempt_rate, comprehension_score, avg_read_seconds, unique_readers
            FROM topic_interest_weekly
            WHERE topic_slug = ? AND locale = ?
            ORDER BY week_start DESC
            LIMIT 12
        """, (topic_slug, locale)).fetchall()
        
        trends = [
            TopicTrendItem(
                week_start=str(r["week_start"]),
                attempt_rate=float(r["attempt_rate"]),
                comprehension_score=float(r["comprehension_score"]),
                avg_read_seconds=float(r["avg_read_seconds"]),
                unique_readers=int(r["unique_readers"])
            )
            for r in rows
        ]
        
        return TopicAnalyticsResponse(
            topic_slug=topic_slug,
            locale=locale,
            trends=trends
        )
    finally:
        conn.close()
