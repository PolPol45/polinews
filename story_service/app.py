#!/usr/bin/env python3
from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

DEFAULT_DB_PATH = Path(os.getenv("POLINEWS_DB_PATH", "data/polinews.db"))

TOPIC_BADGE_COLORS = {
    "politics": "#534AB7",
    "economy": "#185FA5",
    "world": "#0F6E56",
    "technology": "#BA7517",
    "health": "#A32D2D",
    "climate": "#3B6D11",
    "markets": "#993C1D",
    "security": "#444441",
    "business": "#72243E",
    "science": "#085041",
}


@dataclass
class StoryRecord:
    story_id: str
    topic_slug: str
    headline: str
    summary: str
    key_points: list[str]
    sources: list[dict[str, str]]
    published_at: str


def _connect_read_only(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def _human_topic(topic_slug: str) -> str:
    return topic_slug.replace("_", " ").strip().title()


def _truncate_summary(summary: str, limit: int = 320) -> str:
    clean = summary.strip()
    return clean[:limit]


def _required_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _get_story_row(conn: sqlite3.Connection, story_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT story_id, topic_slug, headline, summary, published_at, status
        FROM stories
        WHERE story_id = ?
        LIMIT 1
        """,
        (story_id,),
    ).fetchone()


def _get_story_key_points(conn: sqlite3.Connection, story_id: str) -> list[str]:
    rows = conn.execute(
        """
        SELECT text
        FROM story_key_points
        WHERE story_id = ?
        ORDER BY position ASC
        LIMIT 5
        """,
        (story_id,),
    ).fetchall()
    out: list[str] = []
    for row in rows:
        text = _required_text(row["text"])
        if text:
            out.append(text)
    return out


def _get_story_sources(conn: sqlite3.Connection, story_id: str) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT source_name, COALESCE(canonical_url, source_url) AS source_url
        FROM story_sources
        WHERE story_id = ?
        ORDER BY source_name ASC
        """,
        (story_id,),
    ).fetchall()
    out: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for row in rows:
        source_name = _required_text(row["source_name"])
        source_url = _required_text(row["source_url"])
        if not source_name or not source_url:
            continue
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)
        out.append({"source_name": source_name, "source_url": source_url})
    return out


def _load_story(db_path: Path, story_id: str) -> StoryRecord:
    if not db_path.exists():
        raise HTTPException(status_code=500, detail=f"db_not_found: {db_path}")

    try:
        conn = _connect_read_only(db_path)
    except sqlite3.Error as exc:
        raise HTTPException(status_code=500, detail=f"db_connect_error: {exc}") from exc

    try:
        row = _get_story_row(conn, story_id)
        if row is None:
            raise HTTPException(status_code=404, detail="story_not_found")

        if row["status"] != "publishable":
            raise HTTPException(status_code=410, detail="story_not_publishable")

        headline = _required_text(row["headline"])
        summary = _truncate_summary(_required_text(row["summary"]))
        key_points = _get_story_key_points(conn, story_id)
        sources = _get_story_sources(conn, story_id)

        if not headline or not summary or len(key_points) < 3 or len(sources) < 1:
            raise HTTPException(status_code=410, detail="story_failed_runtime_minimum")

        return StoryRecord(
            story_id=row["story_id"],
            topic_slug=row["topic_slug"],
            headline=headline,
            summary=summary,
            key_points=key_points,
            sources=sources,
            published_at=row["published_at"],
        )
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=500, detail=f"schema_error: {exc}") from exc
    finally:
        conn.close()


def _story_to_contract(story: StoryRecord) -> dict[str, Any]:
    return {
        "story_id": story.story_id,
        "topic_slug": story.topic_slug,
        "headline": story.headline,
        "summary": story.summary,
        "key_points": story.key_points,
        "sources": story.sources,
        "published_at": story.published_at,
        "quiz_available": False,
        "comment_enabled": False,
    }


def _render_story_html(story: StoryRecord, *, auth: bool, balance: int) -> str:
    topic_label = _human_topic(story.topic_slug)
    badge_color = TOPIC_BADGE_COLORS.get(story.topic_slug, "#444441")
    teaser_text = (
        f"You have {balance} credits — answer to earn more"
        if auth
        else "Sign in to earn credits for reading"
    )
    source_links = "\n".join(
        f'<li><a href="{source["source_url"]}" target="_blank" rel="noopener noreferrer">{source["source_name"]}</a></li>'
        for source in story.sources
    )
    key_points = "\n".join(f"<li>{point}</li>" for point in story.key_points[:5])

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{story.headline}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 0; background: #f6f8fb; color: #0f172a; }}
    main {{ max-width: 760px; margin: 24px auto; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; padding: 24px; }}
    .badge {{ display: inline-block; color: #fff; background: {badge_color}; border-radius: 999px; padding: 6px 12px; font-size: 13px; font-weight: 600; }}
    h1 {{ margin: 14px 0; line-height: 1.2; }}
    .snippet {{ color: #334155; line-height: 1.5; margin-bottom: 18px; }}
    section {{ margin-top: 20px; }}
    ul {{ margin: 8px 0 0 20px; }}
    .attribution-label {{ font-weight: 700; margin-bottom: 8px; }}
    .verify-box {{ border: 1px solid #cbd5e1; border-radius: 10px; padding: 14px; background: #f8fafc; }}
    .cta {{ display: inline-block; margin-right: 10px; border: 1px solid #2563eb; color: #2563eb; border-radius: 8px; padding: 6px 10px; text-decoration: none; font-weight: 600; }}
    .credits {{ border-top: 1px solid #e2e8f0; padding-top: 16px; color: #0f172a; font-weight: 600; }}
  </style>
</head>
<body>
  <main>
    <section id="section-topic-badge">
      <span class="badge">{topic_label}</span>
    </section>

    <section id="section-headline">
      <h1>{story.headline}</h1>
    </section>

    <section id="section-snippet">
      <p class="snippet">{story.summary}</p>
    </section>

    <section id="section-key-points">
      <h2>Key points</h2>
      <ul>
        {key_points}
      </ul>
    </section>

    <section id="section-attribution">
      <p class="attribution-label">Summary generated by Poli-News</p>
      <ul>
        {source_links}
      </ul>
    </section>

    <section id="section-verification-box">
      <div class="verify-box">
        <p>Verification will be enabled in W2-04/W2-08. Choose your path:</p>
        <a class="cta" href="#" aria-disabled="true">Start quiz</a>
        <a class="cta" href="#" aria-disabled="true">Add comment</a>
      </div>
    </section>

    <section id="section-credits-teaser" class="credits">
      {teaser_text}
    </section>
  </main>
</body>
</html>
"""


def create_app(db_path: Path | None = None) -> FastAPI:
    resolved_db_path = (db_path or DEFAULT_DB_PATH).resolve()
    app = FastAPI(title="Poli-News Story Service", version="w2-03")

    @app.get("/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "db_path": str(resolved_db_path)}

    @app.get("/stories/{story_id}")
    def get_story(story_id: str) -> dict[str, Any]:
        story = _load_story(resolved_db_path, story_id)
        return _story_to_contract(story)

    @app.get("/stories/{story_id}/page", response_class=HTMLResponse)
    def get_story_page(
        story_id: str,
        auth: int = Query(default=0),
        balance: int = Query(default=30, ge=0, le=100000),
    ) -> HTMLResponse:
        story = _load_story(resolved_db_path, story_id)
        html = _render_story_html(story, auth=auth == 1, balance=balance)
        return HTMLResponse(content=html)

    return app


app = create_app()

