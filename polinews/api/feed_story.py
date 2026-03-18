"""Feed and story API routers."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from polinews.api.auth import get_optional_user
from polinews.config import DB_PATH
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

feed_router = APIRouter(tags=["feed"])
story_router = APIRouter(prefix="/stories", tags=["stories"])

# ── Topic config ──────────────────────────────────────────────────────────────

VALID_TOPICS = {
    "politics", "economy", "world", "technology", "health",
    "climate", "markets", "security", "business", "science",
}

TOPIC_BADGE_COLORS: dict[str, str] = {
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


# ── Pydantic response models ───────────────────────────────────────────────────

class FeedItem(BaseModel):
    story_id: str
    headline: str
    summary_short: str
    topic_slug: str
    published_at: str
    source_count: int
    quiz_available: bool


class FeedResponse(BaseModel):
    items: list[FeedItem]
    topic_slug: str
    page: int
    limit: int
    has_next: bool


class StorySource(BaseModel):
    source_name: str
    source_url: str


class StoryResponse(BaseModel):
    story_id: str
    topic_slug: str
    headline: str
    summary: str
    key_points: list[str]
    sources: list[StorySource]
    published_at: str
    source_count: int
    quiz_available: bool
    comment_enabled: bool


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    return conn


def _story_row(conn: sqlite3.Connection, story_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT story_id, topic_slug, headline, summary, published_at,
               source_count, status, quiz_status
        FROM stories
        WHERE story_id = ?
        LIMIT 1
        """,
        (story_id,),
    ).fetchone()


def _key_points(conn: sqlite3.Connection, story_id: str) -> list[str]:
    rows = conn.execute(
        "SELECT text FROM story_key_points WHERE story_id = ? ORDER BY position ASC LIMIT 5",
        (story_id,),
    ).fetchall()
    return [str(r["text"]).strip() for r in rows if r["text"] and str(r["text"]).strip()]


def _sources(conn: sqlite3.Connection, story_id: str) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT source_name, COALESCE(canonical_url, source_url) AS url
        FROM story_sources
        WHERE story_id = ?
        ORDER BY source_name ASC
        """,
        (story_id,),
    ).fetchall()
    seen: set[str] = set()
    out: list[dict[str, str]] = []
    for r in rows:
        name = str(r["source_name"]).strip()
        url = str(r["url"]).strip()
        if not name or not url or url in seen:
            continue
        seen.add(url)
        out.append({"source_name": name, "source_url": url})
    return out


def _load_story(story_id: str) -> tuple[sqlite3.Row, list[str], list[dict[str, str]]]:
    conn = _conn()
    try:
        row = _story_row(conn, story_id)
        if row is None:
            raise HTTPException(status_code=404, detail="story_not_found")
        if row["status"] != "publishable":
            raise HTTPException(status_code=410, detail="story_not_publishable")
        kps = _key_points(conn, story_id)
        srcs = _sources(conn, story_id)
        if not row["headline"] or not row["summary"] or len(kps) < 3 or len(srcs) < 1:
            raise HTTPException(status_code=410, detail="story_failed_runtime_minimum")
        return row, kps, srcs
    except sqlite3.OperationalError as exc:
        raise HTTPException(status_code=500, detail=f"schema_error: {exc}") from exc
    finally:
        conn.close()


# ── Feed endpoint ─────────────────────────────────────────────────────────────

@feed_router.get("/feed", response_model=FeedResponse)
def get_feed(
    topic: str = Query(..., description="Topic slug e.g. politics, economy"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> FeedResponse:
    """Paginated story feed filtered by topic."""
    if topic not in VALID_TOPICS:
        raise HTTPException(
            status_code=400,
            detail=f"invalid_topic: must be one of {sorted(VALID_TOPICS)}",
        )

    offset = (page - 1) * limit
    conn = _conn()
    try:
        # Fetch one extra to determine has_next
        rows = conn.execute(
            """
            SELECT s.story_id, s.headline, s.summary, s.topic_slug,
                   s.published_at, s.source_count, s.quiz_status
            FROM stories s
            WHERE s.topic_slug = ? AND s.status = 'publishable'
            ORDER BY s.published_at DESC, s.story_id DESC
            LIMIT ? OFFSET ?
            """,
            (topic, limit + 1, offset),
        ).fetchall()
    finally:
        conn.close()

    has_next = len(rows) > limit
    rows = rows[:limit]

    items = [
        FeedItem(
            story_id=str(r["story_id"]),
            headline=str(r["headline"]),
            summary_short=str(r["summary"])[:160],
            topic_slug=str(r["topic_slug"]),
            published_at=str(r["published_at"]),
            source_count=int(r["source_count"] or 1),
            quiz_available=str(r["quiz_status"] or "") == "quiz_available",
        )
        for r in rows
    ]

    return FeedResponse(
        items=items,
        topic_slug=topic,
        page=page,
        limit=limit,
        has_next=has_next,
    )


# ── Story JSON endpoint ────────────────────────────────────────────────────────

@story_router.get("/{story_id}", response_model=StoryResponse)
def get_story(story_id: str) -> StoryResponse:
    """Story page payload — JSON format for frontend consumption."""
    row, kps, srcs = _load_story(story_id)
    return StoryResponse(
        story_id=str(row["story_id"]),
        topic_slug=str(row["topic_slug"]),
        headline=str(row["headline"]),
        summary=str(row["summary"])[:320],
        key_points=kps,
        sources=[StorySource(**s) for s in srcs],
        published_at=str(row["published_at"]),
        source_count=int(row["source_count"] or 1),
        quiz_available=str(row["quiz_status"] or "") == "quiz_available",
        comment_enabled=False,
    )


# ── Story HTML endpoint ────────────────────────────────────────────────────────

@story_router.get("/{story_id}/page", response_class=HTMLResponse)
def get_story_page(
    story_id: str,
    auth: int = Query(default=0),
    balance: int = Query(default=30, ge=0, le=100_000),
    current_user: Annotated[dict[str, str] | None, Depends(get_optional_user)] = None,
) -> HTMLResponse:
    """Rendered HTML story page."""
    row, kps, srcs = _load_story(story_id)

    is_auth = auth == 1 or current_user is not None
    topic_label = str(row["topic_slug"]).replace("_", " ").title()
    badge_color = TOPIC_BADGE_COLORS.get(str(row["topic_slug"]), "#444441")
    quiz_available = str(row["quiz_status"] or "") == "quiz_available"

    teaser = (
        f"You have {balance} credits — answer to earn more"
        if is_auth
        else "Sign in to earn credits for reading"
    )
    source_links = "\n".join(
        f'<li><a href="{s["source_url"]}" target="_blank" rel="noopener noreferrer">{s["source_name"]}</a></li>'
        for s in srcs
    )
    key_points_html = "\n".join(f"<li>{p}</li>" for p in kps[:5])

    quiz_cta = (
        f'<a class="cta" href="/quiz?story_id={quote(story_id)}" id="btn-start-quiz">Start quiz</a>'
        if quiz_available
        else '<span class="cta disabled" aria-disabled="true">Quiz not available</span>'
    )

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>{row["headline"]}</title>
  <meta name="description" content="{str(row["summary"])[:160]}"/>
  <style>
    body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;margin:0;background:#f6f8fb;color:#0f172a;}}
    main{{max-width:760px;margin:24px auto;background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:24px;}}
    .badge{{display:inline-block;color:#fff;background:{badge_color};border-radius:999px;padding:6px 12px;font-size:13px;font-weight:600;}}
    h1{{margin:14px 0;line-height:1.2;}}
    .snippet{{color:#334155;line-height:1.5;margin-bottom:18px;}}
    section{{margin-top:20px;}}
    ul{{margin:8px 0 0 20px;}}
    .attr-label{{font-weight:700;margin-bottom:8px;}}
    .verify-box{{border:1px solid #cbd5e1;border-radius:10px;padding:14px;background:#f8fafc;}}
    .cta{{display:inline-block;margin-right:10px;border:1px solid #2563eb;color:#2563eb;border-radius:8px;padding:6px 10px;text-decoration:none;font-weight:600;}}
    .cta.disabled{{border-color:#94a3b8;color:#94a3b8;cursor:not-allowed;}}
    .credits{{border-top:1px solid #e2e8f0;padding-top:16px;color:#0f172a;font-weight:600;}}
    .disclaimer{{font-size:11px;color:#94a3b8;margin-top:6px;}}
  </style>
</head>
<body>
  <main>
    <section id="section-topic-badge"><span class="badge">{topic_label}</span></section>
    <section id="section-headline"><h1>{row["headline"]}</h1></section>
    <section id="section-snippet"><p class="snippet">{str(row["summary"])[:320]}</p></section>
    <section id="section-key-points"><h2>Key points</h2><ul>{key_points_html}</ul></section>
    <section id="section-attribution">
      <p class="attr-label">Sources</p>
      <ul>{source_links}</ul>
      <p class="disclaimer">Summary generated by Poli-News from public source metadata</p>
    </section>
    <section id="section-verification-box">
      <div class="verify-box">
        <p>Verify your reading to earn credits:</p>
        {quiz_cta}
        <a class="cta" href="#" id="btn-comment" aria-disabled="true">Add comment</a>
      </div>
    </section>
    <section id="section-credits-teaser" class="credits">{teaser}</section>
  </main>
</body>
</html>"""
    return HTMLResponse(content=html)
