#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from collector.config import (
    DEFAULT_DB_PATH,
    DEFAULT_LOG_DIR,
    KEYPOINTS_BACKOFF_SECONDS,
    KEYPOINTS_MAX_RETRIES,
    KEYPOINTS_MAX_STORIES_PER_RUN,
    KEYPOINTS_MODEL,
    KEYPOINTS_TIMEOUT_SECONDS,
    OLLAMA_BASE_URL,
    USER_AGENT,
)
from collector.db import (
    connect_db,
    ensure_schema,
    fetch_keypoint_candidates,
    fetch_story_source_links,
    replace_story_key_points,
    update_story_publishability,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_backoff_csv(value: str) -> tuple[int, ...]:
    chunks = [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    if not chunks:
        return tuple()
    return tuple(int(chunk) for chunk in chunks)


class KeypointsLogger:
    def __init__(self, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        self.run_log_path = log_dir / "keypoints_runs.log"
        self.reject_log_path = log_dir / "keypoints_rejects.log"
        self.run_log_path.touch(exist_ok=True)
        self.reject_log_path.touch(exist_ok=True)

    def log_run(
        self,
        *,
        run_id: str,
        start_ts: str,
        end_ts: str,
        processed: int,
        generated: int,
        publishable_count: int,
        not_publishable_count: int,
        avg_latency_ms: int,
        error_class: str,
    ) -> None:
        line = (
            f"{run_id},{start_ts},{end_ts},{processed},{generated},"
            f"{publishable_count},{not_publishable_count},{avg_latency_ms},{error_class}"
        )
        with self.run_log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
        print(f"[KEYPOINTS_RUN] {line}")

    def log_reject(self, *, run_id: str, story_id: str, reason_code: str, latency_ms: int, timestamp: str) -> None:
        line = f"{run_id},{story_id},{reason_code},{latency_ms},{timestamp}"
        with self.reject_log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
        print(f"[KEYPOINTS_REJECT] {line}")


def build_prompt(headline: str, snippet: str, topic_slug: str, sources: list[tuple[str, str]]) -> str:
    source_lines = "\n".join(f"- {name}: {url}" for name, url in sources[:5]) or "- no_sources"
    return (
        "You are generating key points for a news summary page. "
        "Return only valid JSON with this exact schema: {\"key_points\": [\"...\"]}. "
        "Rules: produce 3 to 5 short readable points, no duplicates, no markdown bullets, "
        "no invented facts, align strictly to the provided headline/snippet/sources.\n\n"
        f"Topic: {topic_slug}\n"
        f"Headline: {headline}\n"
        f"Snippet: {snippet}\n"
        f"Sources:\n{source_lines}\n"
    )


def parse_key_points_payload(text: str) -> tuple[list[str] | None, str]:
    payload: dict[str, Any] | None = None
    try:
        candidate = json.loads(text)
        if isinstance(candidate, dict):
            payload = candidate
    except json.JSONDecodeError:
        payload = None

    if payload is None:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return None, "keypoints_invalid_json"
        try:
            candidate = json.loads(match.group(0))
            if isinstance(candidate, dict):
                payload = candidate
        except json.JSONDecodeError:
            return None, "keypoints_invalid_json"

    if payload is None:
        return None, "keypoints_invalid_json"

    points = payload.get("key_points")
    if not isinstance(points, list):
        return None, "keypoints_invalid_json"
    return [str(item) for item in points], ""


def validate_key_points(points: list[str]) -> tuple[list[str] | None, str]:
    cleaned = [collapse_spaces(point) for point in points]
    if any(not point for point in cleaned):
        return None, "keypoints_empty"

    if len(cleaned) < 3 or len(cleaned) > 5:
        return None, "keypoints_invalid_count"

    dedup_check = {point.casefold() for point in cleaned}
    if len(dedup_check) != len(cleaned):
        return None, "keypoints_duplicates"

    if any(len(point) > 220 for point in cleaned):
        return None, "keypoints_too_long"

    return cleaned, ""


def call_ollama(
    *,
    base_url: str,
    model: str,
    prompt: str,
    timeout_seconds: int,
    max_retries: int,
    backoff_seconds: tuple[int, ...],
) -> tuple[str | None, str]:
    endpoint = base_url.rstrip("/") + "/api/generate"
    request_payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
        },
    }

    for attempt in range(max_retries + 1):
        try:
            req = Request(
                endpoint,
                data=json.dumps(request_payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": USER_AGENT,
                },
                method="POST",
            )
            with urlopen(req, timeout=timeout_seconds) as response:
                data = json.loads(response.read().decode("utf-8"))
            content = data.get("response")
            if not isinstance(content, str):
                return None, "keypoints_invalid_json"
            return content, ""
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            if attempt < max_retries and backoff_seconds:
                backoff = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                time.sleep(backoff)
                continue
            return None, "keypoints_generation_failed"

    return None, "keypoints_generation_failed"


def generate_key_points(
    *,
    base_url: str,
    model: str,
    timeout_seconds: int,
    max_retries: int,
    backoff_seconds: tuple[int, ...],
    headline: str,
    snippet: str,
    topic_slug: str,
    sources: list[tuple[str, str]],
) -> tuple[list[str] | None, str, int]:
    started = time.perf_counter()
    prompt = build_prompt(headline=headline, snippet=snippet, topic_slug=topic_slug, sources=sources)
    raw_text, error = call_ollama(
        base_url=base_url,
        model=model,
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )
    if error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return None, error, latency_ms

    points, parse_error = parse_key_points_payload(raw_text or "")
    if parse_error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return None, parse_error, latency_ms

    validated, validation_error = validate_key_points(points or [])
    latency_ms = int((time.perf_counter() - started) * 1000)
    if validation_error:
        return None, validation_error, latency_ms

    return validated, "", latency_ms


def run_once(
    *,
    db_path: Path,
    log_dir: Path,
    ollama_base_url: str,
    model: str,
    timeout_seconds: int,
    max_retries: int,
    backoff_seconds: tuple[int, ...],
    max_stories: int,
) -> int:
    if not db_path.exists():
        raise RuntimeError(f"db_not_found: {db_path}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    start_ts = utc_now_iso()
    logger = KeypointsLogger(log_dir)

    processed = 0
    generated = 0
    publishable_count = 0
    not_publishable_count = 0
    total_latency_ms = 0
    error_class = ""

    conn = connect_db(db_path)
    ensure_schema(conn)

    try:
        candidates = fetch_keypoint_candidates(conn, limit=max_stories)
        for story in candidates:
            processed += 1
            story_id = story["story_id"]
            sources = fetch_story_source_links(conn, story_id=story_id)

            points, reason_code, latency_ms = generate_key_points(
                base_url=ollama_base_url,
                model=model,
                timeout_seconds=timeout_seconds,
                max_retries=max_retries,
                backoff_seconds=backoff_seconds,
                headline=story["headline"],
                snippet=story["summary"],
                topic_slug=story["topic_slug"],
                sources=sources,
            )
            total_latency_ms += latency_ms

            generated_at = utc_now_iso()
            if points is None:
                not_publishable_count += 1
                update_story_publishability(
                    conn,
                    story_id=story_id,
                    status="not_publishable",
                    publishability_reason=reason_code,
                    keypoints_generated_at=generated_at,
                )
                logger.log_reject(
                    run_id=run_id,
                    story_id=story_id,
                    reason_code=reason_code,
                    latency_ms=latency_ms,
                    timestamp=generated_at,
                )
                continue

            replace_story_key_points(conn, story_id=story_id, key_points=points, created_at=generated_at)
            update_story_publishability(
                conn,
                story_id=story_id,
                status="publishable",
                publishability_reason=None,
                keypoints_generated_at=generated_at,
            )
            generated += 1
            publishable_count += 1

        conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        error_class = f"runtime_error:{type(exc).__name__}"
        raise
    finally:
        end_ts = utc_now_iso()
        avg_latency_ms = int(total_latency_ms / processed) if processed else 0
        logger.log_run(
            run_id=run_id,
            start_ts=start_ts,
            end_ts=end_ts,
            processed=processed,
            generated=generated,
            publishable_count=publishable_count,
            not_publishable_count=not_publishable_count,
            avg_latency_ms=avg_latency_ms,
            error_class=error_class,
        )
        conn.close()

    print(
        "[KEYPOINTS_SUMMARY] "
        f"run_id={run_id} processed={processed} generated={generated} "
        f"publishable={publishable_count} not_publishable={not_publishable_count}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poli-News key points generator (local Ollama)")
    parser.add_argument("--run-once", action="store_true", help="Generate key points once on candidate stories")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--ollama-base-url", type=str, default=OLLAMA_BASE_URL)
    parser.add_argument("--model", type=str, default=KEYPOINTS_MODEL)
    parser.add_argument("--timeout-seconds", type=int, default=KEYPOINTS_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=KEYPOINTS_MAX_RETRIES)
    parser.add_argument(
        "--backoff-seconds",
        type=str,
        default=",".join(str(i) for i in KEYPOINTS_BACKOFF_SECONDS),
        help="Comma-separated backoff seconds, e.g. 1,3",
    )
    parser.add_argument("--max-stories", type=int, default=KEYPOINTS_MAX_STORIES_PER_RUN)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.run_once:
        print("Error: only --run-once mode is supported in W2-02.", file=sys.stderr)
        return 1

    try:
        return run_once(
            db_path=args.db_path,
            log_dir=args.log_dir,
            ollama_base_url=args.ollama_base_url,
            model=args.model,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
            backoff_seconds=parse_backoff_csv(args.backoff_seconds),
            max_stories=args.max_stories,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[KEYPOINTS_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
