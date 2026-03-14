from __future__ import annotations

import json
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def connect_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS feed_items_raw (
          raw_id TEXT PRIMARY KEY,
          feed_id TEXT NOT NULL,
          fetched_at TIMESTAMP NOT NULL,
          title TEXT,
          snippet TEXT,
          source_name TEXT,
          source_url TEXT,
          published_at TIMESTAMP,
          payload_json TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_feed_items_raw_feed_fetched
        ON feed_items_raw(feed_id, fetched_at);
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stories (
          story_id TEXT PRIMARY KEY,
          topic_slug TEXT NOT NULL,
          headline TEXT NOT NULL,
          summary TEXT NOT NULL,
          published_at TIMESTAMP NOT NULL,
          source_count INTEGER NOT NULL DEFAULT 1,
          created_at TIMESTAMP NOT NULL,
          status TEXT NOT NULL DEFAULT 'not_publishable',
          publishability_reason TEXT,
          keypoints_generated_at TIMESTAMP
        );
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS story_sources (
          story_source_id TEXT PRIMARY KEY,
          story_id TEXT NOT NULL,
          source_name TEXT NOT NULL,
          source_url TEXT NOT NULL,
          canonical_url TEXT,
          publisher_domain TEXT NOT NULL,
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_story_sources_story_id
        ON story_sources(story_id);
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS story_key_points (
          key_point_id TEXT PRIMARY KEY,
          story_id TEXT NOT NULL,
          position INTEGER NOT NULL,
          text TEXT NOT NULL,
          created_at TIMESTAMP NOT NULL,
          UNIQUE(story_id, position),
          FOREIGN KEY (story_id) REFERENCES stories(story_id)
        );
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_story_key_points_story_id
        ON story_key_points(story_id, position);
        """
    )
    _ensure_story_sources_canonical_column(conn)
    _ensure_stories_publishability_columns(conn)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dedup_registry (
          dedup_key TEXT PRIMARY KEY,
          story_id TEXT NOT NULL,
          raw_id TEXT NOT NULL,
          created_at TIMESTAMP NOT NULL
        );
        """
    )
    conn.commit()


def insert_feed_item_raw(
    conn: sqlite3.Connection,
    *,
    raw_id: str,
    feed_id: str,
    fetched_at: str,
    title: str | None,
    snippet: str | None,
    source_name: str | None,
    source_url: str | None,
    published_at: str | None,
    payload: dict[str, Any],
) -> None:
    conn.execute(
        """
        INSERT INTO feed_items_raw (
          raw_id, feed_id, fetched_at, title, snippet, source_name, source_url, published_at, payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            raw_id,
            feed_id,
            fetched_at,
            title,
            snippet,
            source_name,
            source_url,
            published_at,
            json.dumps(payload, ensure_ascii=False),
        ),
    )


@dataclass
class RawFeedItem:
    raw_id: str
    feed_id: str
    fetched_at: str
    title: str | None
    snippet: str | None
    source_name: str | None
    source_url: str | None
    published_at: str | None
    payload_json: str


def fetch_feed_items_raw(
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
    offset: int = 0,
) -> list[RawFeedItem]:
    query = """
        SELECT
          raw_id, feed_id, fetched_at, title, snippet, source_name, source_url, published_at, payload_json
        FROM feed_items_raw
        ORDER BY fetched_at ASC, raw_id ASC
    """
    params: tuple[Any, ...]
    if limit is None:
        params = ()
    else:
        query += " LIMIT ? OFFSET ?"
        params = (limit, offset)

    rows = conn.execute(query, params).fetchall()
    return [
        RawFeedItem(
            raw_id=row[0],
            feed_id=row[1],
            fetched_at=row[2],
            title=row[3],
            snippet=row[4],
            source_name=row[5],
            source_url=row[6],
            published_at=row[7],
            payload_json=row[8],
        )
        for row in rows
    ]


def insert_story(
    conn: sqlite3.Connection,
    *,
    story_id: str,
    topic_slug: str,
    headline: str,
    summary: str,
    published_at: str,
    source_count: int,
    created_at: str,
    status: str = "not_publishable",
    publishability_reason: str | None = None,
    keypoints_generated_at: str | None = None,
) -> bool:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO stories (
          story_id, topic_slug, headline, summary, published_at, source_count, created_at,
          status, publishability_reason, keypoints_generated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            story_id,
            topic_slug,
            headline,
            summary,
            published_at,
            source_count,
            created_at,
            status,
            publishability_reason,
            keypoints_generated_at,
        ),
    )
    if cursor.rowcount == 0 and publishability_reason:
        conn.execute(
            """
            UPDATE stories
            SET publishability_reason = COALESCE(publishability_reason, ?)
            WHERE story_id = ?
            """,
            (publishability_reason, story_id),
        )
    return cursor.rowcount > 0


def insert_story_source(
    conn: sqlite3.Connection,
    *,
    story_source_id: str,
    story_id: str,
    source_name: str,
    source_url: str,
    canonical_url: str | None,
    publisher_domain: str,
) -> bool:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO story_sources (
          story_source_id, story_id, source_name, source_url, canonical_url, publisher_domain
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (story_source_id, story_id, source_name, source_url, canonical_url, publisher_domain),
    )
    if cursor.rowcount == 0 and canonical_url:
        # Backfill canonical_url for pre-W1-06 rows created before this column existed.
        conn.execute(
            """
            UPDATE story_sources
            SET canonical_url = ?
            WHERE story_source_id = ?
              AND (canonical_url IS NULL OR TRIM(canonical_url) = '')
            """,
            (canonical_url, story_source_id),
        )
    return cursor.rowcount > 0


def dedup_key_exists(conn: sqlite3.Connection, *, dedup_key: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM dedup_registry WHERE dedup_key = ? LIMIT 1",
        (dedup_key,),
    ).fetchone()
    return row is not None


def insert_dedup_registry(
    conn: sqlite3.Connection,
    *,
    dedup_key: str,
    story_id: str,
    raw_id: str,
    created_at: str,
) -> bool:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO dedup_registry (
          dedup_key, story_id, raw_id, created_at
        ) VALUES (?, ?, ?, ?)
        """,
        (dedup_key, story_id, raw_id, created_at),
    )
    return cursor.rowcount > 0


def fetch_keypoint_candidates(conn: sqlite3.Connection, *, limit: int) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT s.story_id, s.headline, s.summary, s.topic_slug
        FROM stories s
        LEFT JOIN (
          SELECT story_id, COUNT(*) AS kp_count
          FROM story_key_points
          GROUP BY story_id
        ) kp ON kp.story_id = s.story_id
        WHERE s.status != 'publishable' OR COALESCE(kp.kp_count, 0) < 3
        ORDER BY s.created_at ASC, s.story_id ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        {
            "story_id": row[0],
            "headline": row[1],
            "summary": row[2],
            "topic_slug": row[3],
        }
        for row in rows
    ]


def fetch_story_source_links(conn: sqlite3.Connection, *, story_id: str) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT source_name, COALESCE(canonical_url, source_url)
        FROM story_sources
        WHERE story_id = ?
        ORDER BY source_name ASC
        """,
        (story_id,),
    ).fetchall()
    links: list[tuple[str, str]] = []
    for source_name, source_url in rows:
        if not source_name or not source_url:
            continue
        links.append((str(source_name), str(source_url)))
    return links


def replace_story_key_points(
    conn: sqlite3.Connection,
    *,
    story_id: str,
    key_points: Sequence[str],
    created_at: str,
) -> None:
    conn.execute("DELETE FROM story_key_points WHERE story_id = ?", (story_id,))
    for idx, text in enumerate(key_points, start=1):
        key_point_id = f"{story_id}_kp_{idx}"
        conn.execute(
            """
            INSERT INTO story_key_points (
              key_point_id, story_id, position, text, created_at
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (key_point_id, story_id, idx, text, created_at),
        )


def update_story_publishability(
    conn: sqlite3.Connection,
    *,
    story_id: str,
    status: str,
    publishability_reason: str | None,
    keypoints_generated_at: str | None,
) -> None:
    conn.execute(
        """
        UPDATE stories
        SET status = ?,
            publishability_reason = ?,
            keypoints_generated_at = ?
        WHERE story_id = ?
        """,
        (status, publishability_reason, keypoints_generated_at, story_id),
    )


def count_story_key_points(conn: sqlite3.Connection, *, story_id: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM story_key_points WHERE story_id = ?",
        (story_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _ensure_story_sources_canonical_column(conn: sqlite3.Connection) -> None:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(story_sources)").fetchall()]
    if "canonical_url" not in columns:
        conn.execute("ALTER TABLE story_sources ADD COLUMN canonical_url TEXT")


def _ensure_stories_publishability_columns(conn: sqlite3.Connection) -> None:
    columns = [row[1] for row in conn.execute("PRAGMA table_info(stories)").fetchall()]
    if "status" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN status TEXT NOT NULL DEFAULT 'not_publishable'")
    if "publishability_reason" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN publishability_reason TEXT")
    if "keypoints_generated_at" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN keypoints_generated_at TIMESTAMP")
