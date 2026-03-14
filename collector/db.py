from __future__ import annotations

import json
import sqlite3
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

