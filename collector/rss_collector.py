#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from collector.collector_logging import CollectorLogger, utc_now_iso
from collector.config import (
    BACKOFF_SECONDS,
    DEFAULT_DB_PATH,
    DEFAULT_FEEDS_CSV,
    DEFAULT_LOG_DIR,
    DEFAULT_STATE_PATH,
    MAX_RETRIES,
    REQUEST_TIMEOUT_SECONDS,
    STALE_THRESHOLD,
    USER_AGENT,
)
from collector.db import connect_db, ensure_schema, insert_feed_item_raw
from collector.parser import FeedParseError, ParsedItem, parse_feed


@dataclass
class FeedConfig:
    feed_id: str
    url: str
    status: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_active_feeds(csv_path: Path) -> list[FeedConfig]:
    feeds: list[FeedConfig] = []
    with csv_path.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            status = (row.get("status") or "").strip().lower()
            if status != "active":
                continue
            feed_id = (row.get("feed_id") or "").strip()
            url = (row.get("url") or "").strip()
            if not feed_id or not url:
                continue
            feeds.append(FeedConfig(feed_id=feed_id, url=url, status=status))
    return feeds


def fetch_with_retry(url: str) -> bytes:
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            req = Request(url, headers={"User-Agent": USER_AGENT})
            with urlopen(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                return resp.read()
        except (URLError, HTTPError, TimeoutError, ValueError) as exc:
            last_error = exc
            # Fallback for constrained networking environments.
            try:
                return _fetch_with_curl(url)
            except Exception as curl_exc:  # noqa: BLE001
                last_error = curl_exc
            if attempt < MAX_RETRIES:
                backoff = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
                time.sleep(backoff)
    raise RuntimeError(f"fetch_failed: {last_error}")


def _fetch_with_curl(url: str) -> bytes:
    result = subprocess.run(
        [
            "curl",
            "-L",
            "-sS",
            "--max-time",
            str(REQUEST_TIMEOUT_SECONDS),
            "-A",
            USER_AGENT,
            url,
        ],
        check=True,
        capture_output=True,
    )
    return result.stdout


def validate_item(item: ParsedItem) -> str | None:
    if not item.title:
        return "missing_title"
    if not item.link:
        return "missing_link"
    if item.source_name:
        return None
    domain = urlparse(item.link).netloc if item.link else ""
    if not domain:
        return "missing_source_or_domain"
    return None


def load_stale_state(state_path: Path) -> dict[str, int]:
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_stale_state(state_path: Path, state: dict[str, int]) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")


def run_once(feeds_csv: Path, db_path: Path, log_dir: Path, state_path: Path) -> int:
    if not feeds_csv.exists():
        raise RuntimeError(f"feeds_csv_not_found: {feeds_csv}")

    feeds = load_active_feeds(feeds_csv)
    if not feeds:
        raise RuntimeError("no_active_feeds_found")

    logger = CollectorLogger(log_dir=log_dir)
    conn = connect_db(db_path=db_path)
    ensure_schema(conn)
    stale_state = load_stale_state(state_path)

    total_inserted = 0
    for feed in feeds:
        start_ts = _utc_now()
        fetched_count = 0
        accepted_count = 0
        rejected_count = 0
        error_class = ""
        fetched_at = _utc_now()

        try:
            xml_payload = fetch_with_retry(feed.url)
            parsed_items = parse_feed(xml_payload)
            fetched_count = len(parsed_items)

            for item in parsed_items:
                reason = validate_item(item)
                if reason:
                    rejected_count += 1
                    logger.log_reject(
                        feed_id=feed.feed_id,
                        item_ref=item.item_ref,
                        reason_code=reason,
                        reject_ts=utc_now_iso(),
                    )
                    continue

                published_at = item.published_at or fetched_at
                insert_feed_item_raw(
                    conn,
                    raw_id=str(uuid.uuid4()),
                    feed_id=feed.feed_id,
                    fetched_at=fetched_at,
                    title=item.title,
                    snippet=item.snippet,
                    source_name=item.source_name,
                    source_url=item.source_url,
                    published_at=published_at,
                    payload=item.payload,
                )
                accepted_count += 1
                total_inserted += 1

            stale_state[feed.feed_id] = 0
            conn.commit()
        except FeedParseError:
            error_class = "parse_error"
            rejected_count += 1
            stale_state[feed.feed_id] = stale_state.get(feed.feed_id, 0) + 1
            logger.log_reject(
                feed_id=feed.feed_id,
                item_ref="-",
                reason_code="parse_error",
                reject_ts=utc_now_iso(),
            )
        except Exception:
            error_class = "fetch_error"
            rejected_count += 1
            stale_state[feed.feed_id] = stale_state.get(feed.feed_id, 0) + 1
            logger.log_reject(
                feed_id=feed.feed_id,
                item_ref="-",
                reason_code="fetch_error",
                reject_ts=utc_now_iso(),
            )

        if stale_state.get(feed.feed_id, 0) >= STALE_THRESHOLD:
            error_class = (
                f"{error_class};stale_threshold_reached"
                if error_class
                else "stale_threshold_reached"
            )

        end_ts = _utc_now()
        logger.log_run(
            feed_id=feed.feed_id,
            start_ts=start_ts,
            end_ts=end_ts,
            fetched_count=fetched_count,
            accepted_count=accepted_count,
            rejected_count=rejected_count,
            error_class=error_class,
        )

    save_stale_state(state_path=state_path, state=stale_state)
    print(f"[SUMMARY] feeds={len(feeds)} inserted={total_inserted} db={db_path}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poli-News RSS collector")
    parser.add_argument("--run-once", action="store_true", help="Run collector once on all active feeds")
    parser.add_argument("--feeds-csv", type=Path, default=DEFAULT_FEEDS_CSV)
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--state-path", type=Path, default=DEFAULT_STATE_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.run_once:
        print("Error: only --run-once mode is supported in W1-04.", file=sys.stderr)
        return 1
    try:
        return run_once(
            feeds_csv=args.feeds_csv,
            db_path=args.db_path,
            log_dir=args.log_dir,
            state_path=args.state_path,
        )
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
