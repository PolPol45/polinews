"""
Analytics aggregation job.
Processes reading_sessions, attempts, and comments into story_analytics and topic_interest_weekly.
"""
from __future__ import annotations

import logging
import sqlite3
import time
from datetime import date, datetime, timedelta, timezone

from polinews.config import DB_PATH
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

log = logging.getLogger("polinews.worker.analytics")


def aggregate_story_metrics(conn: sqlite3.Connection, target_date: date | None = None) -> int:
    """
    Run the aggregation job for a specific date (defaults to today).
    Updates story_analytics table.
    Returns the number of stories processed.
    """
    if target_date is None:
        target_date = date.today()
    date_str = target_date.isoformat()
    
    # 1. Get all stories that had activity on this date
    # Activity includes: sessions started or attempts created
    stories_query = """
        SELECT DISTINCT story_id FROM (
            SELECT story_id FROM reading_sessions WHERE DATE(started_at) = ?
            UNION
            SELECT story_id FROM attempts WHERE DATE(created_at) = ?
            UNION
            SELECT story_id FROM comments WHERE DATE(created_at) = ?
        )
    """
    story_ids = [r[0] for r in conn.execute(stories_query, (date_str, date_str, date_str)).fetchall()]
    
    processed = 0
    for sid in story_ids:
        # Aggregation of sessions
        sessions_metrics = conn.execute("""
            SELECT 
                COUNT(*) as box_viewed,
                AVG(active_seconds) as avg_active,
                AVG(scroll_depth) as avg_scroll
            FROM reading_sessions
            WHERE story_id = ? AND DATE(started_at) = ?
        """, (sid, date_str)).fetchone()
        
        # Aggregation of attempts
        attempt_metrics = conn.execute("""
            SELECT 
                COUNT(*) as quiz_started,
                SUM(CASE WHEN passed = 1 THEN 1 ELSE 0 END) as quiz_passed
            FROM attempts
            WHERE story_id = ? AND DATE(created_at) = ?
        """, (sid, date_str)).fetchone()
        
        # Aggregation of comments
        comment_metrics = conn.execute("""
            SELECT 
                COUNT(*) as comment_submitted,
                SUM(CASE WHEN status = 'accepted' THEN 1 ELSE 0 END) as comment_accepted
            FROM comments
            WHERE story_id = ? AND DATE(created_at) = ?
        """, (sid, date_str)).fetchone()
        
        # Calculate derived metrics
        quiz_started = int(attempt_metrics["quiz_started"] or 0)
        quiz_passed = int(attempt_metrics["quiz_passed"] or 0)
        box_viewed = int(sessions_metrics["box_viewed"] or 0)
        
        comp_score = (quiz_passed / quiz_started) if quiz_started > 0 else 0.0
        
        # Engagement Score formula placeholder
        # 40% comprehension, 30% read time (normalized to 60s), 30% comments
        avg_active = float(sessions_metrics["avg_active"] or 0.0)
        comment_rate = (int(comment_metrics["comment_accepted"] or 0) / int(comment_metrics["comment_submitted"] or 1)) if int(comment_metrics["comment_submitted"] or 0) > 0 else 0.0
        
        eng_score = (0.4 * comp_score + 0.3 * min(1.0, avg_active/60.0) + 0.3 * comment_rate) * 100
        
        analytics_id = f"{sid}_{date_str}"
        conn.execute("""
            INSERT INTO story_analytics 
            (analytics_id, story_id, date, box_viewed, quiz_started, quiz_passed, 
             comment_submitted, comment_accepted, avg_active_seconds, 
             avg_scroll_depth, comprehension_score, engagement_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(analytics_id) DO UPDATE SET
                box_viewed = EXCLUDED.box_viewed,
                quiz_started = EXCLUDED.quiz_started,
                quiz_passed = EXCLUDED.quiz_passed,
                comment_submitted = EXCLUDED.comment_submitted,
                comment_accepted = EXCLUDED.comment_accepted,
                avg_active_seconds = EXCLUDED.avg_active_seconds,
                avg_scroll_depth = EXCLUDED.avg_scroll_depth,
                comprehension_score = EXCLUDED.comprehension_score,
                engagement_score = EXCLUDED.engagement_score
        """, (
            analytics_id, sid, date_str, box_viewed, quiz_started, quiz_passed, 
            int(comment_metrics["comment_submitted"] or 0), int(comment_metrics["comment_accepted"] or 0), 
            avg_active, float(sessions_metrics["avg_scroll"] or 0.0), 
            round(comp_score, 4), round(eng_score, 2)
        ))
        processed += 1
        
    return processed


def aggregate_topic_metrics(conn: sqlite3.Connection, target_date: date | None = None) -> int:
    """
    Run the aggregation job for topic-level metrics.
    Updates topic_interest_weekly table.
    """
    if target_date is None:
        target_date = date.today()
        
    # Find the start of the current week (Monday)
    week_start = target_date - timedelta(days=target_date.weekday())
    week_start_str = week_start.isoformat()
    
    # Aggregate by topic and locale
    topic_metrics_query = """
        SELECT 
            topic_slug, 
            locale,
            COUNT(DISTINCT user_id) as unique_readers,
            AVG(active_seconds) as avg_read_seconds,
            SUM(quiz_started) as total_quiz_started,
            SUM(quiz_passed) as total_quiz_passed,
            SUM(box_viewed) as total_box_viewed
        FROM (
            SELECT 
                topic_slug, 
                locale, 
                user_id, 
                active_seconds,
                COALESCE((SELECT COUNT(*) FROM attempts a WHERE a.user_id = rs.user_id AND a.story_id = rs.story_id AND DATE(a.created_at) >= ?), 0) as quiz_started,
                COALESCE((SELECT COUNT(*) FROM attempts a WHERE a.user_id = rs.user_id AND a.story_id = rs.story_id AND passed = 1 AND DATE(a.created_at) >= ?), 0) as quiz_passed,
                1 as box_viewed
            FROM reading_sessions rs
            WHERE DATE(started_at) >= ?
        )
        GROUP BY topic_slug, locale
    """
    
    rows = conn.execute(topic_metrics_query, (week_start_str, week_start_str, week_start_str)).fetchall()
    processed = 0
    for r in rows:
        attempt_rate = (r["total_quiz_started"] / r["total_box_viewed"]) if r["total_box_viewed"] > 0 else 0.0
        comp_score = (r["total_quiz_passed"] / r["total_quiz_started"]) if r["total_quiz_started"] > 0 else 0.0
        
        conn.execute("""
            INSERT INTO topic_interest_weekly 
            (week_start, topic_slug, locale, attempt_rate, comprehension_score, avg_read_seconds, unique_readers)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(week_start, topic_slug, locale) DO UPDATE SET
                attempt_rate = EXCLUDED.attempt_rate,
                comprehension_score = EXCLUDED.comprehension_score,
                avg_read_seconds = EXCLUDED.avg_read_seconds,
                unique_readers = EXCLUDED.unique_readers
        """, (
            week_start_str, r["topic_slug"], r["locale"], 
            round(attempt_rate, 4), round(comp_score, 4), 
            round(r["avg_read_seconds"] or 0, 2), int(r["unique_readers"] or 0)
        ))
        processed += 1
        
    return processed


def run_analytics_once() -> None:
    """Manually trigger the full analytics aggregation."""
    log.info("[worker] analytics: start")
    t0 = time.perf_counter()
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    try:
        sp = aggregate_story_metrics(conn)
        tp = aggregate_topic_metrics(conn)
        conn.commit()
        log.info("[worker] analytics: done in %.1fs (stories=%d, topics=%d)", 
                 time.perf_counter() - t0, sp, tp)
    except Exception:
        log.exception("[worker] analytics: FAILED")
    finally:
        conn.close()
