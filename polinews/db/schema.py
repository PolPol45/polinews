"""
Full database schema for Poli-News.

Calling ensure_schema(conn) is idempotent — safe to call on every startup.
All ALTER TABLE migrations are additive (never destructive).
"""
from __future__ import annotations

import sqlite3


def ensure_schema(conn: sqlite3.Connection) -> None:
    """Create all tables and indexes. Safe to call repeatedly."""
    _create_ingestion_tables(conn)
    _create_story_tables(conn)
    _create_quiz_tables(conn)
    _create_user_tables(conn)
    _create_reward_tables(conn)
    _create_metric_tables(conn)
    _run_migrations(conn)
    conn.commit()


# ── Ingestion ─────────────────────────────────────────────────────────────────

def _create_ingestion_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS feed_items_raw (
          raw_id        TEXT PRIMARY KEY,
          feed_id       TEXT NOT NULL,
          fetched_at    TIMESTAMP NOT NULL,
          title         TEXT,
          snippet       TEXT,
          source_name   TEXT,
          source_url    TEXT,
          published_at  TIMESTAMP,
          payload_json  TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_feed_items_raw_feed_fetched
        ON feed_items_raw(feed_id, fetched_at)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS dedup_registry (
          dedup_key   TEXT PRIMARY KEY,
          story_id    TEXT NOT NULL,
          raw_id      TEXT NOT NULL,
          created_at  TIMESTAMP NOT NULL
        )
    """)


# ── Stories ───────────────────────────────────────────────────────────────────

def _create_story_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stories (
          story_id                TEXT PRIMARY KEY,
          topic_slug              TEXT NOT NULL,
          headline                TEXT NOT NULL,
          summary                 TEXT NOT NULL,
          published_at            TIMESTAMP NOT NULL,
          source_count            INTEGER NOT NULL DEFAULT 1,
          created_at              TIMESTAMP NOT NULL,
          status                  TEXT NOT NULL DEFAULT 'not_publishable',
          publishability_reason   TEXT,
          keypoints_generated_at  TIMESTAMP,
          quiz_status             TEXT,
          quiz_unavailable_reason TEXT,
          quiz_pool_version       INTEGER,
          quiz_updated_at         TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stories_topic_published
        ON stories(topic_slug, published_at DESC)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_stories_status
        ON stories(status, quiz_status)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS story_sources (
          story_source_id   TEXT PRIMARY KEY,
          story_id          TEXT NOT NULL,
          source_name       TEXT NOT NULL,
          source_url        TEXT NOT NULL,
          canonical_url     TEXT,
          publisher_domain  TEXT NOT NULL,
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_story_sources_story_id
        ON story_sources(story_id)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS story_key_points (
          key_point_id  TEXT PRIMARY KEY,
          story_id      TEXT NOT NULL,
          position      INTEGER NOT NULL,
          text          TEXT NOT NULL,
          created_at    TIMESTAMP NOT NULL,
          UNIQUE(story_id, position),
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_story_key_points_story_id
        ON story_key_points(story_id, position)
    """)


# ── Quizzes ───────────────────────────────────────────────────────────────────

def _create_quiz_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quizzes (
          quiz_id             TEXT PRIMARY KEY,
          story_id            TEXT NOT NULL,
          version             INTEGER NOT NULL,
          question_pool_size  INTEGER NOT NULL,
          pool_signature      TEXT,
          generator_version   TEXT,
          created_at          TIMESTAMP NOT NULL,
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_quizzes_story_version
        ON quizzes(story_id, version DESC)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS quiz_questions (
          question_id           TEXT PRIMARY KEY,
          quiz_id               TEXT NOT NULL,
          question_text         TEXT NOT NULL,
          task_type             TEXT NOT NULL DEFAULT 'comprehension',
          options_json          TEXT,
          correct_option_id     TEXT,
          annotation_campaign_id TEXT,
          created_at            TIMESTAMP NOT NULL,
          FOREIGN KEY (quiz_id) REFERENCES quizzes(quiz_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_quiz_questions_quiz
        ON quiz_questions(quiz_id)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
          attempt_id              TEXT PRIMARY KEY,
          user_id                 TEXT NOT NULL,
          story_id                TEXT NOT NULL,
          quiz_id                 TEXT NOT NULL,
          answers_json            TEXT NOT NULL,
          score_raw               REAL NOT NULL,
          passed                  INTEGER NOT NULL,  -- 0/1
          client_elapsed_seconds  INTEGER,
          created_at              TIMESTAMP NOT NULL,
          FOREIGN KEY (user_id)  REFERENCES users(user_id),
          FOREIGN KEY (story_id) REFERENCES stories(story_id),
          FOREIGN KEY (quiz_id)  REFERENCES quizzes(quiz_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_attempts_user_story_date
        ON attempts(user_id, story_id, created_at DESC)
    """)


# ── Users ─────────────────────────────────────────────────────────────────────

def _create_user_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
          user_id          TEXT PRIMARY KEY,
          email            TEXT UNIQUE NOT NULL,
          created_at       TIMESTAMP NOT NULL,
          reputation       INTEGER NOT NULL DEFAULT 100,
          onboarding_state TEXT NOT NULL DEFAULT 'new'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS magic_link_tokens (
          token       TEXT PRIMARY KEY,
          user_id     TEXT NOT NULL,
          email       TEXT NOT NULL,
          expires_at  TIMESTAMP NOT NULL,
          used_at     TIMESTAMP,
          FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_magic_link_email
        ON magic_link_tokens(email, used_at)
    """)


# ── Rewards ───────────────────────────────────────────────────────────────────

def _create_reward_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rewards_ledger (
          entry_id      TEXT PRIMARY KEY,
          user_id       TEXT NOT NULL,
          story_id      TEXT,
          delta_credits INTEGER NOT NULL,
          reason        TEXT NOT NULL,
          reference_id  TEXT,
          created_at    TIMESTAMP NOT NULL,
          FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ledger_user_date
        ON rewards_ledger(user_id, created_at DESC)
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ledger_quiz_pass_unique
        ON rewards_ledger(user_id, story_id)
        WHERE reason = 'quiz_pass'
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS comments (
          comment_id    TEXT PRIMARY KEY,
          user_id       TEXT NOT NULL,
          story_id      TEXT NOT NULL,
          text          TEXT NOT NULL,
          status        TEXT NOT NULL DEFAULT 'pending_review',
          reject_reason TEXT,
          created_at    TIMESTAMP NOT NULL,
          reviewed_at   TIMESTAMP,
          UNIQUE(user_id, story_id),
          FOREIGN KEY (user_id)  REFERENCES users(user_id),
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS fraud_signals (
          signal_id    TEXT PRIMARY KEY,
          user_id      TEXT NOT NULL,
          signal_type  TEXT NOT NULL,
          severity     TEXT NOT NULL DEFAULT 'low',
          details_json TEXT,
          attempt_id   TEXT,
          created_at   TIMESTAMP NOT NULL,
          resolved_at  TIMESTAMP,
          resolution   TEXT,
          FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_fraud_signals_user
        ON fraud_signals(user_id, resolved_at)
    """)


# ── Metrics ───────────────────────────────────────────────────────────────────

def _create_metric_tables(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS reading_sessions (
          session_id      TEXT PRIMARY KEY,
          user_id         TEXT NOT NULL,
          story_id        TEXT NOT NULL,
          topic_slug      TEXT NOT NULL,
          started_at      TIMESTAMP NOT NULL,
          scroll_depth    INTEGER,
          active_seconds  INTEGER,
          total_seconds   INTEGER,
          device_type     TEXT,
          locale          TEXT,
          FOREIGN KEY (user_id)  REFERENCES users(user_id),
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_reading_sessions_story
        ON reading_sessions(story_id, started_at DESC)
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS story_analytics (
          analytics_id        TEXT PRIMARY KEY,
          story_id            TEXT NOT NULL,
          date                DATE NOT NULL,
          box_viewed          INTEGER NOT NULL DEFAULT 0,
          quiz_started        INTEGER NOT NULL DEFAULT 0,
          quiz_passed         INTEGER NOT NULL DEFAULT 0,
          comment_submitted   INTEGER NOT NULL DEFAULT 0,
          comment_accepted    INTEGER NOT NULL DEFAULT 0,
          avg_active_seconds  REAL,
          avg_scroll_depth    REAL,
          comprehension_score REAL,
          engagement_score    REAL,
          UNIQUE(story_id, date),
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS topic_interest_weekly (
          week_start          DATE NOT NULL,
          topic_slug          TEXT NOT NULL,
          locale              TEXT NOT NULL DEFAULT 'all',
          attempt_rate        REAL,
          comprehension_score REAL,
          avg_read_seconds    REAL,
          unique_readers      INTEGER,
          PRIMARY KEY(week_start, topic_slug, locale)
        )
    """)


# ── Migrations (additive ALTER TABLE for pre-existing DBs) ───────────────────

def _run_migrations(conn: sqlite3.Connection) -> None:
    """Add missing columns to existing tables — never drops or renames."""
    _add_column_if_missing(conn, "stories", "quiz_status", "TEXT")
    _add_column_if_missing(conn, "stories", "quiz_unavailable_reason", "TEXT")
    _add_column_if_missing(conn, "stories", "quiz_pool_version", "INTEGER")
    _add_column_if_missing(conn, "stories", "quiz_updated_at", "TIMESTAMP")
    _add_column_if_missing(conn, "stories", "status", "TEXT NOT NULL DEFAULT 'not_publishable'")
    _add_column_if_missing(conn, "stories", "publishability_reason", "TEXT")
    _add_column_if_missing(conn, "stories", "keypoints_generated_at", "TIMESTAMP")
    _add_column_if_missing(conn, "story_sources", "canonical_url", "TEXT")
    _add_column_if_missing(conn, "quizzes", "pool_signature", "TEXT")
    _add_column_if_missing(conn, "quizzes", "generator_version", "TEXT")
    _add_column_if_missing(conn, "quiz_questions", "task_type", "TEXT NOT NULL DEFAULT 'comprehension'")
    _add_column_if_missing(conn, "quiz_questions", "options_json", "TEXT")
    _add_column_if_missing(conn, "quiz_questions", "correct_option_id", "TEXT")
    _add_column_if_missing(conn, "quiz_questions", "annotation_campaign_id", "TEXT")


def _add_column_if_missing(
    conn: sqlite3.Connection,
    table: str,
    column: str,
    col_def: str,
) -> None:
    try:
        existing = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except sqlite3.OperationalError:
        return  # table doesn't exist yet — will be created fresh
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
