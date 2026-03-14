from __future__ import annotations

import json
import sqlite3
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
          created_at TIMESTAMP NOT NULL
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
) -> bool:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO stories (
          story_id, topic_slug, headline, summary, published_at, source_count, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (story_id, topic_slug, headline, summary, published_at, source_count, created_at),
    )
    return cursor.rowcount > 0


def insert_story_source(
    conn: sqlite3.Connection,
    *,
    story_source_id: str,
    story_id: str,
    source_name: str,
    source_url: str,
    publisher_domain: str,
) -> bool:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO story_sources (
          story_source_id, story_id, source_name, source_url, publisher_domain
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (story_source_id, story_id, source_name, source_url, publisher_domain),
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
