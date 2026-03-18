#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import re
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from polinews.collector.canonical_url import normalize_canonical_url, resolve_canonical_url
from polinews.collector.config import (
    CANONICAL_RESOLVE_BACKOFF_SECONDS,
    CANONICAL_RESOLVE_MAX_RETRIES,
    CANONICAL_RESOLVE_TIMEOUT_SECONDS,
    DEDUP_WINDOW_HOURS,
    DEFAULT_DB_PATH,
    DEFAULT_FEEDS_CSV,
    DEFAULT_LOG_DIR,
)
from polinews.collector.db import (
    RawFeedItem,
    connect_db,
    dedup_key_exists,
    ensure_schema,
    fetch_feed_items_raw,
    insert_dedup_registry,
    insert_story,
    insert_story_source,
)
from polinews.collector.dedup import DEDUP_REASON_CODE, build_dedup_key, build_title_fingerprint

DEFAULT_TOPICS_FILE = Path("docs/mvp_offchain/specs/topics_v1.md")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def strip_markup(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value)


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = html.unescape(value)
    cleaned = strip_markup(cleaned)
    cleaned = collapse_spaces(cleaned)
    return cleaned or None


def parse_payload(payload_json: str) -> dict[str, Any]:
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_snippet(raw_snippet: str | None, payload: dict[str, Any]) -> str | None:
    candidate = clean_text(raw_snippet)
    if candidate:
        return candidate
    for key in ("snippet", "description", "summary", "content"):
        candidate = clean_text(payload.get(key))
        if candidate:
            return candidate
    return None


def parse_datetime_utc(value: str | None) -> str | None:
    if not value:
        return None

    # RFC822 style dates from RSS.
    try:
        parsed = parsedate_to_datetime(value)
        if parsed is not None:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass

    # ISO-like dates from Atom.
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def normalize_url(url: str | None) -> str | None:
    """Backwards-compatible alias for tests/callers."""
    return normalize_canonical_url(url)


def domain_from_url(url: str | None) -> str | None:
    if not url:
        return None
    try:
        host = urlsplit(url).netloc.strip().lower()
    except ValueError:
        return None
    return host or None


def deterministic_story_id(raw_id: str) -> str:
    digest = hashlib.sha1(raw_id.encode("utf-8")).hexdigest()  # noqa: S324
    return f"story_{digest[:24]}"


def deterministic_story_source_id(story_id: str, source_url: str) -> str:
    key = f"{story_id}|{source_url}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()  # noqa: S324
    return f"ss_{digest[:24]}"


def load_topic_slugs(topics_file: Path) -> set[str]:
    slugs: set[str] = set()
    for line in topics_file.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        parts = [part.strip() for part in line.split("|")]
        if len(parts) < 4:
            continue
        if parts[1].lower() in {"topic", "---"}:
            continue
        slug = parts[2]
        if slug and slug.lower() != "slug" and slug != "---":
            slugs.add(slug)
    return slugs


def load_feed_topic_map(feeds_csv: Path) -> dict[str, str]:
    mapping: dict[str, str] = {}
    with feeds_csv.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            feed_id = (row.get("feed_id") or "").strip()
            topic_slug = (row.get("topic_slug") or "").strip()
            if feed_id and topic_slug:
                mapping[feed_id] = topic_slug
    return mapping


@dataclass
class Rejection:
    raw_id: str
    feed_id: str
    reason_code: str


class NormalizerLogger:
    def __init__(self, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        self.run_log_path = log_dir / "normalization_runs.log"
        self.reject_log_path = log_dir / "normalization_rejects.log"
        self.run_log_path.touch(exist_ok=True)
        self.reject_log_path.touch(exist_ok=True)

    def log_run(
        self,
        *,
        run_id: str,
        start_ts: str,
        end_ts: str,
        processed: int,
        accepted: int,
        rejected: int,
        duplicates_count: int,
        canonical_resolved_count: int,
        canonical_fallback_count: int,
        canonical_error_count: int,
        error_class: str,
    ) -> None:
        line = (
            f"{run_id},{start_ts},{end_ts},{processed},{accepted},{rejected},"
            f"{duplicates_count},{canonical_resolved_count},{canonical_fallback_count},"
            f"{canonical_error_count},{error_class}"
        )
        self._append(self.run_log_path, line)
        print(f"[NORMALIZE_RUN] {line}")

    def log_reject(self, *, run_id: str, raw_id: str, feed_id: str, reason_code: str, reject_ts: str) -> None:
        safe_raw = raw_id.replace("\n", " ").replace(",", ";")[:200]
        line = f"{run_id},{safe_raw},{feed_id},{reason_code},{reject_ts}"
        self._append(self.reject_log_path, line)
        print(f"[NORMALIZE_REJECT] {line}")

    @staticmethod
    def _append(path: Path, line: str) -> None:
        with path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")


def normalize_item(
    item: RawFeedItem,
    *,
    feed_topic_map: dict[str, str],
    valid_topics: set[str],
    normalization_ts: str,
    canonical_timeout_seconds: int,
    canonical_max_retries: int,
    canonical_backoff_seconds: Iterable[int],
) -> tuple[dict[str, Any] | None, Rejection | None]:
    payload = parse_payload(item.payload_json)

    topic_slug = feed_topic_map.get(item.feed_id)
    if not topic_slug or topic_slug not in valid_topics:
        return None, Rejection(raw_id=item.raw_id, feed_id=item.feed_id, reason_code="invalid_topic_slug")

    title = clean_text(item.title or payload.get("title"))
    if not title:
        return None, Rejection(raw_id=item.raw_id, feed_id=item.feed_id, reason_code="missing_title")

    snippet = extract_snippet(item.snippet, payload)
    if not snippet:
        return None, Rejection(raw_id=item.raw_id, feed_id=item.feed_id, reason_code="missing_snippet")

    source_url = normalize_canonical_url(item.source_url) or normalize_canonical_url(payload.get("source_url"))
    canonical_url, resolution_mode, canonical_error = resolve_canonical_url(
        payload.get("link"),
        source_url,
        timeout_seconds=canonical_timeout_seconds,
        max_retries=canonical_max_retries,
        backoff_seconds=canonical_backoff_seconds,
    )
    if not canonical_url:
        reason = canonical_error or "invalid_canonical_url"
        return None, Rejection(raw_id=item.raw_id, feed_id=item.feed_id, reason_code=reason)

    source_url = source_url or canonical_url
    publisher_domain = domain_from_url(source_url) or domain_from_url(canonical_url)

    source_name = clean_text(item.source_name or payload.get("source_name")) or publisher_domain
    if not source_name or not publisher_domain:
        return None, Rejection(raw_id=item.raw_id, feed_id=item.feed_id, reason_code="missing_source_or_domain")

    published_at = parse_datetime_utc(item.published_at or payload.get("published_at"))
    if not published_at:
        published_at = parse_datetime_utc(item.fetched_at)
        if not published_at:
            return None, Rejection(raw_id=item.raw_id, feed_id=item.feed_id, reason_code="invalid_published_at")

    story_id = deterministic_story_id(item.raw_id)
    story_source_id = deterministic_story_source_id(story_id, source_url)

    normalized = {
        "story": {
            "story_id": story_id,
            "topic_slug": topic_slug,
            "headline": title,
            "summary": snippet,
            "published_at": published_at,
            "source_count": 1,
            "created_at": normalization_ts,
            "status": "not_publishable",
            "publishability_reason": "missing_key_points",
            "keypoints_generated_at": None,
        },
        "story_source": {
            "story_source_id": story_source_id,
            "story_id": story_id,
            "source_name": source_name,
            "source_url": source_url,
            "canonical_url": canonical_url,
            "publisher_domain": publisher_domain,
        },
        "_canonical_resolution_mode": resolution_mode,
    }
    return normalized, None


def run_once(
    db_path: Path,
    feeds_csv: Path,
    topics_file: Path,
    log_dir: Path,
    dedup_window_hours: int,
    canonical_timeout_seconds: int,
    canonical_max_retries: int,
    canonical_backoff_seconds: tuple[int, ...],
) -> int:
    if not db_path.exists():
        raise RuntimeError(f"db_not_found: {db_path}")
    if not feeds_csv.exists():
        raise RuntimeError(f"feeds_csv_not_found: {feeds_csv}")
    if not topics_file.exists():
        raise RuntimeError(f"topics_file_not_found: {topics_file}")

    run_id = hashlib.sha1(utc_now_iso().encode("utf-8")).hexdigest()[:12]  # noqa: S324
    start_ts = utc_now_iso()

    logger = NormalizerLogger(log_dir)
    conn = connect_db(db_path)
    ensure_schema(conn)

    feed_topic_map = load_feed_topic_map(feeds_csv)
    valid_topics = load_topic_slugs(topics_file)
    items = fetch_feed_items_raw(conn)

    processed = 0
    accepted = 0
    rejected = 0
    duplicates_count = 0
    canonical_resolved_count = 0
    canonical_fallback_count = 0
    canonical_error_count = 0
    error_class = ""
    normalization_ts = utc_now_iso()

    try:
        for item in items:
            processed += 1
            normalized, rejection = normalize_item(
                item,
                feed_topic_map=feed_topic_map,
                valid_topics=valid_topics,
                normalization_ts=normalization_ts,
                canonical_timeout_seconds=canonical_timeout_seconds,
                canonical_max_retries=canonical_max_retries,
                canonical_backoff_seconds=canonical_backoff_seconds,
            )
            if rejection:
                rejected += 1
                if rejection.reason_code == "invalid_canonical_url":
                    canonical_error_count += 1
                logger.log_reject(
                    run_id=run_id,
                    raw_id=rejection.raw_id,
                    feed_id=rejection.feed_id,
                    reason_code=rejection.reason_code,
                    reject_ts=utc_now_iso(),
                )
                continue

            story = normalized["story"]
            story_source = normalized["story_source"]
            resolution_mode = normalized["_canonical_resolution_mode"]
            if resolution_mode in {"resolved_direct", "resolved_redirect"}:
                canonical_resolved_count += 1
            elif resolution_mode == "fallback_source":
                canonical_fallback_count += 1
            else:
                canonical_error_count += 1
            title_fingerprint = build_title_fingerprint(story["headline"])
            dedup_key = build_dedup_key(
                title_fingerprint=title_fingerprint,
                publisher_domain=story_source["publisher_domain"],
                url_normalized=story_source["canonical_url"] or story_source["source_url"],
                published_at_iso=story["published_at"],
                window_hours=dedup_window_hours,
            )

            if dedup_key_exists(conn, dedup_key=dedup_key):
                duplicates_count += 1
                rejected += 1
                logger.log_reject(
                    run_id=run_id,
                    raw_id=item.raw_id,
                    feed_id=item.feed_id,
                    reason_code=DEDUP_REASON_CODE,
                    reject_ts=utc_now_iso(),
                )
                continue

            insert_story(conn, **story)
            insert_story_source(conn, **story_source)
            insert_dedup_registry(
                conn,
                dedup_key=dedup_key,
                story_id=story["story_id"],
                raw_id=item.raw_id,
                created_at=normalization_ts,
            )
            accepted += 1

        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        error_class = f"runtime_error:{type(exc).__name__}"
        raise
    finally:
        end_ts = utc_now_iso()
        logger.log_run(
            run_id=run_id,
            start_ts=start_ts,
            end_ts=end_ts,
            processed=processed,
            accepted=accepted,
            rejected=rejected,
            duplicates_count=duplicates_count,
            canonical_resolved_count=canonical_resolved_count,
            canonical_fallback_count=canonical_fallback_count,
            canonical_error_count=canonical_error_count,
            error_class=error_class,
        )
        conn.close()

    print(
        "[NORMALIZE_SUMMARY] "
        f"run_id={run_id} processed={processed} accepted={accepted} "
        f"rejected={rejected} duplicates={duplicates_count} "
        f"canonical_resolved={canonical_resolved_count} "
        f"canonical_fallback={canonical_fallback_count} "
        f"canonical_error={canonical_error_count}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poli-News feed normalizer")
    parser.add_argument("--run-once", action="store_true", help="Run normalizer once on feed_items_raw")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--feeds-csv", type=Path, default=DEFAULT_FEEDS_CSV)
    parser.add_argument("--topics-file", type=Path, default=DEFAULT_TOPICS_FILE)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--dedup-window-hours", type=int, default=DEDUP_WINDOW_HOURS)
    parser.add_argument("--canonical-timeout-seconds", type=int, default=CANONICAL_RESOLVE_TIMEOUT_SECONDS)
    parser.add_argument("--canonical-max-retries", type=int, default=CANONICAL_RESOLVE_MAX_RETRIES)
    parser.add_argument(
        "--canonical-backoff-seconds",
        type=str,
        default=",".join(str(i) for i in CANONICAL_RESOLVE_BACKOFF_SECONDS),
        help="Comma-separated backoff seconds, e.g. 1,3,9",
    )
    return parser.parse_args()


def parse_backoff_csv(value: str) -> tuple[int, ...]:
    chunks = [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    if not chunks:
        return tuple()
    return tuple(int(chunk) for chunk in chunks)


def main() -> int:
    args = parse_args()
    if not args.run_once:
        print("Error: only --run-once mode is supported in W1-05.", file=sys.stderr)
        return 1

    try:
        return run_once(
            db_path=args.db_path,
            feeds_csv=args.feeds_csv,
            topics_file=args.topics_file,
            log_dir=args.log_dir,
            dedup_window_hours=args.dedup_window_hours,
            canonical_timeout_seconds=args.canonical_timeout_seconds,
            canonical_max_retries=args.canonical_max_retries,
            canonical_backoff_seconds=parse_backoff_csv(args.canonical_backoff_seconds),
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[NORMALIZE_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
