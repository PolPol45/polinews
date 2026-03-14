#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
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

from collector.config import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_LOG_DIR,
    KEYPOINTS_MODEL,
    OLLAMA_BASE_URL,
    QUIZ_POOL_BACKOFF_SECONDS,
    QUIZ_POOL_ENABLED,
    QUIZ_POOL_GENERATOR_VERSION,
    QUIZ_POOL_MAX_RETRIES,
    QUIZ_POOL_MAX_STORIES_PER_RUN,
    QUIZ_POOL_MIN_SIZE,
    QUIZ_POOL_MODEL,
    QUIZ_POOL_TARGET_SIZE,
    QUIZ_POOL_TIMEOUT_SECONDS,
    USER_AGENT,
)
from collector.db import (  # noqa: E402
    connect_db,
    count_publishable_stories,
    count_quiz_available_stories,
    ensure_schema,
    fetch_latest_quiz_metadata,
    fetch_quiz_pool_candidates,
    fetch_story_key_points_texts,
    fetch_story_source_links,
    insert_quiz,
    insert_quiz_questions,
    update_story_quiz_state,
)

REASON_POOL_TOO_SMALL = "pool_too_small"
REASON_POOL_QUALITY_FAILED = "pool_quality_failed"
REASON_STORY_NOT_PUBLISHABLE = "story_not_publishable"
REASON_QUIZ_GENERATION_FAILED = "quiz_generation_failed"
REASON_QUIZ_TEMP_DISABLED = "quiz_temporarily_disabled"

QUESTION_TYPES = {"comprehension", "detail"}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def collapse_spaces(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def parse_backoff_csv(value: str) -> tuple[int, ...]:
    chunks = [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    if not chunks:
        return tuple()
    return tuple(int(chunk) for chunk in chunks)


class QuizPoolLogger:
    def __init__(self, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        self.run_log_path = log_dir / "quiz_pool_runs.log"
        self.reject_log_path = log_dir / "quiz_pool_rejects.log"
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
        available: int,
        not_available: int,
        skipped_unchanged: int,
        coverage_percent: float,
        avg_latency_ms: int,
        error_class: str,
    ) -> None:
        line = (
            f"{run_id},{start_ts},{end_ts},{processed},{generated},{available},{not_available},"
            f"{skipped_unchanged},{coverage_percent:.2f},{avg_latency_ms},{error_class}"
        )
        with self.run_log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
        print(f"[QUIZ_POOL_RUN] {line}")

    def log_reject(
        self,
        *,
        run_id: str,
        story_id: str,
        reason_code: str,
        details: str,
        latency_ms: int,
        timestamp: str,
    ) -> None:
        safe_details = details.replace("\n", " ").replace(",", ";")[:240]
        line = f"{run_id},{story_id},{reason_code},{safe_details},{latency_ms},{timestamp}"
        with self.reject_log_path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
        print(f"[QUIZ_POOL_REJECT] {line}")


def build_prompt(
    *,
    story_id: str,
    topic_slug: str,
    headline: str,
    summary: str,
    key_points: list[str],
    sources: list[tuple[str, str]],
    target_size: int,
) -> str:
    kp_lines = "\n".join(f"- {point}" for point in key_points[:5])
    source_lines = "\n".join(f"- {name}: {url}" for name, url in sources[:5])
    return (
        "You generate candidate quiz pools for verified-reading checks. "
        "Return ONLY valid JSON with this schema: "
        "{\"questions\":[{\"question_text\":\"...\",\"task_type\":\"comprehension|detail\","
        "\"options\":[{\"option_id\":\"a\",\"text\":\"...\"}],\"correct_option_id\":\"a\"}]}. "
        "Create concise, factual questions based only on provided inputs. "
        f"Produce around {target_size} questions if possible.\n\n"
        f"Story ID: {story_id}\n"
        f"Topic: {topic_slug}\n"
        f"Headline: {headline}\n"
        f"Summary: {summary}\n"
        f"Key points:\n{kp_lines or '- none'}\n"
        f"Sources:\n{source_lines or '- none'}\n"
    )


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
        "format": "json",
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
                payload = json.loads(response.read().decode("utf-8"))
            content = payload.get("response")
            if not isinstance(content, str):
                return None, REASON_QUIZ_GENERATION_FAILED
            return content, ""
        except (HTTPError, URLError, TimeoutError, ValueError, json.JSONDecodeError):
            if attempt < max_retries and backoff_seconds:
                delay = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                time.sleep(delay)
                continue
            return None, REASON_QUIZ_GENERATION_FAILED

    return None, REASON_QUIZ_GENERATION_FAILED


def parse_questions_payload(text: str) -> tuple[list[dict[str, Any]] | None, str]:
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
            return None, REASON_QUIZ_GENERATION_FAILED
        try:
            candidate = json.loads(match.group(0))
            if isinstance(candidate, dict):
                payload = candidate
        except json.JSONDecodeError:
            return None, REASON_QUIZ_GENERATION_FAILED

    if payload is None:
        return None, REASON_QUIZ_GENERATION_FAILED

    questions = payload.get("questions")
    if not isinstance(questions, list):
        return None, REASON_QUIZ_GENERATION_FAILED

    return [q for q in questions if isinstance(q, dict)], ""


def _normalize_task_type(value: Any) -> str:
    text = collapse_spaces(str(value or "").lower())
    if text == "detail":
        return "detail"
    return "comprehension"


def _normalize_options(value: Any) -> list[dict[str, str]]:
    options: list[dict[str, str]] = []
    if not isinstance(value, list):
        return options

    for idx, raw_option in enumerate(value, start=1):
        option_id = f"o{idx}"
        option_text = ""
        if isinstance(raw_option, dict):
            option_id_candidate = collapse_spaces(str(raw_option.get("option_id") or ""))
            if option_id_candidate:
                option_id = option_id_candidate
            option_text = collapse_spaces(str(raw_option.get("text") or ""))
        else:
            option_text = collapse_spaces(str(raw_option))

        if not option_text:
            continue
        options.append({"option_id": option_id, "text": option_text})

    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for option in options:
        key = option["text"].casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(option)
    return deduped


def _normalize_correct_option_id(raw_correct: Any, options: list[dict[str, str]]) -> str | None:
    if not options:
        return None

    option_ids = [option["option_id"] for option in options]
    by_text = {option["text"].casefold(): option["option_id"] for option in options}

    if isinstance(raw_correct, int):
        if 0 <= raw_correct < len(option_ids):
            return option_ids[raw_correct]
        if 1 <= raw_correct <= len(option_ids):
            return option_ids[raw_correct - 1]

    correct_text = collapse_spaces(str(raw_correct or ""))
    if not correct_text:
        return None

    if correct_text in option_ids:
        return correct_text

    return by_text.get(correct_text.casefold())


def _select_questions_with_mix(
    questions: list[dict[str, Any]],
    *,
    target_size: int,
) -> list[dict[str, Any]]:
    if len(questions) <= target_size:
        return questions

    comprehension = [q for q in questions if q["task_type"] == "comprehension"]
    detail = [q for q in questions if q["task_type"] == "detail"]
    selected: list[dict[str, Any]] = []

    if comprehension:
        selected.append(comprehension[0])
    if detail:
        selected.append(detail[0])

    selected_keys = {q["question_text"].casefold() for q in selected}
    for question in questions:
        if len(selected) >= target_size:
            break
        key = question["question_text"].casefold()
        if key in selected_keys:
            continue
        selected.append(question)
        selected_keys.add(key)

    return selected


def validate_questions(
    questions: list[dict[str, Any]],
    *,
    min_size: int,
    target_size: int,
) -> tuple[list[dict[str, Any]] | None, str]:
    normalized: list[dict[str, Any]] = []
    seen_questions: set[str] = set()

    for raw_question in questions:
        question_text = collapse_spaces(str(raw_question.get("question_text") or raw_question.get("text") or ""))
        if not question_text:
            continue

        key = question_text.casefold()
        if key in seen_questions:
            continue
        seen_questions.add(key)

        options = _normalize_options(raw_question.get("options"))
        if len(options) < 2:
            continue

        correct_option_id = _normalize_correct_option_id(raw_question.get("correct_option_id"), options)
        if not correct_option_id:
            continue

        task_type = _normalize_task_type(raw_question.get("task_type") or raw_question.get("type"))
        if task_type not in QUESTION_TYPES:
            continue

        normalized.append(
            {
                "question_text": question_text,
                "task_type": task_type,
                "options": options,
                "correct_option_id": correct_option_id,
            }
        )

    if len(normalized) < min_size:
        return None, REASON_POOL_TOO_SMALL

    limited = _select_questions_with_mix(normalized, target_size=target_size)
    types = {question["task_type"] for question in limited}
    if "comprehension" not in types or "detail" not in types:
        return None, REASON_POOL_QUALITY_FAILED

    if len(limited) < min_size or len(limited) > target_size:
        return None, REASON_POOL_QUALITY_FAILED

    return limited, ""


def _fallback_options(correct_text: str, distractors: list[str]) -> list[dict[str, str]]:
    options: list[dict[str, str]] = [{"option_id": "a", "text": collapse_spaces(correct_text)}]
    next_id = ord("b")
    for distractor in distractors:
        clean = collapse_spaces(distractor)
        if not clean:
            continue
        if clean.casefold() == options[0]["text"].casefold():
            continue
        options.append({"option_id": chr(next_id), "text": clean})
        next_id += 1
        if len(options) >= 4:
            break
    return options


def build_fallback_questions(
    *,
    story: dict[str, str],
    key_points: list[str],
    sources: list[tuple[str, str]],
    target_size: int,
) -> list[dict[str, Any]]:
    fallback_questions: list[dict[str, Any]] = []
    clean_points = [collapse_spaces(point) for point in key_points if collapse_spaces(point)]
    source_names = [collapse_spaces(name) for name, _ in sources if collapse_spaces(name)]

    if clean_points:
        q1_options = _fallback_options(
            clean_points[0],
            clean_points[1:] + [story["headline"], story["summary"]],
        )
        if len(q1_options) >= 3:
            fallback_questions.append(
                {
                    "question_text": "Which statement is explicitly supported by this story summary?",
                    "task_type": "comprehension",
                    "options": q1_options,
                    "correct_option_id": "a",
                }
            )

    if source_names:
        distractor_sources = ["Associated Press", "Financial Times", "The Guardian", "Al Jazeera"]
        q2_options = _fallback_options(source_names[0], distractor_sources + source_names[1:])
        if len(q2_options) >= 3:
            fallback_questions.append(
                {
                    "question_text": "Which source is cited in this Poli-News story page?",
                    "task_type": "detail",
                    "options": q2_options,
                    "correct_option_id": "a",
                }
            )

    topic_value = story["topic_slug"].replace("_", " ").title()
    q3_options = _fallback_options(topic_value, ["World", "Technology", "Health", "Economy"])
    if len(q3_options) >= 3:
        fallback_questions.append(
            {
                "question_text": "Which topic badge matches this story?",
                "task_type": "detail",
                "options": q3_options,
                "correct_option_id": "a",
            }
        )

    if len(clean_points) >= 2:
        q4_options = _fallback_options(clean_points[1], [clean_points[0], story["headline"], topic_value])
        if len(q4_options) >= 3:
            fallback_questions.append(
                {
                    "question_text": "Which point appears among the listed key points?",
                    "task_type": "comprehension",
                    "options": q4_options,
                    "correct_option_id": "a",
                }
            )

    for idx, point in enumerate(clean_points[2:], start=5):
        q_options = _fallback_options(point, clean_points[:2] + [topic_value, story["headline"]])
        if len(q_options) < 3:
            continue
        fallback_questions.append(
            {
                "question_text": f"Which option matches key point #{idx - 2} from this story?",
                "task_type": "detail" if idx % 2 == 0 else "comprehension",
                "options": q_options,
                "correct_option_id": "a",
            }
        )
        if len(fallback_questions) >= target_size:
            break

    return fallback_questions[:target_size]


def build_pool_signature(
    *,
    generator_version: str,
    model: str,
    story: dict[str, str],
    key_points: list[str],
    sources: list[tuple[str, str]],
) -> str:
    canonical_payload = {
        "generator_version": generator_version,
        "model": model,
        "story_id": story["story_id"],
        "topic_slug": story["topic_slug"],
        "headline": collapse_spaces(story["headline"]),
        "summary": collapse_spaces(story["summary"]),
        "key_points": [collapse_spaces(point) for point in key_points],
        "sources": [{"name": name, "url": url} for name, url in sources],
    }
    serialized = json.dumps(canonical_payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(serialized.encode("utf-8")).hexdigest()  # noqa: S324


def generate_questions_for_story(
    *,
    story: dict[str, str],
    key_points: list[str],
    sources: list[tuple[str, str]],
    ollama_base_url: str,
    model: str,
    timeout_seconds: int,
    max_retries: int,
    backoff_seconds: tuple[int, ...],
    target_size: int,
    min_size: int,
) -> tuple[list[dict[str, Any]] | None, str, int]:
    started = time.perf_counter()
    prompt = build_prompt(
        story_id=story["story_id"],
        topic_slug=story["topic_slug"],
        headline=story["headline"],
        summary=story["summary"],
        key_points=key_points,
        sources=sources,
        target_size=target_size,
    )
    raw_text, generation_error = call_ollama(
        base_url=ollama_base_url,
        model=model,
        prompt=prompt,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=backoff_seconds,
    )
    if generation_error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return None, generation_error, latency_ms

    parsed_questions, parse_error = parse_questions_payload(raw_text or "")
    if parse_error:
        latency_ms = int((time.perf_counter() - started) * 1000)
        return None, parse_error, latency_ms

    validated, validation_error = validate_questions(
        parsed_questions or [],
        min_size=min_size,
        target_size=target_size,
    )
    if validation_error:
        # Fallback synthesizer completes pools when model output is too short/noisy.
        fallback_questions = build_fallback_questions(
            story=story,
            key_points=key_points,
            sources=sources,
            target_size=target_size,
        )
        merged = (parsed_questions or []) + fallback_questions
        validated, validation_error = validate_questions(
            merged,
            min_size=min_size,
            target_size=target_size,
        )
    latency_ms = int((time.perf_counter() - started) * 1000)
    if validation_error:
        return None, validation_error, latency_ms

    return validated, "", latency_ms


def build_quiz_id(story_id: str, version: int) -> str:
    digest = hashlib.sha1(f"{story_id}|{version}".encode("utf-8")).hexdigest()  # noqa: S324
    return f"quiz_{digest[:24]}"


def attach_question_ids(quiz_id: str, questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for idx, question in enumerate(questions, start=1):
        item = dict(question)
        item["question_id"] = f"{quiz_id}_q{idx}"
        enriched.append(item)
    return enriched


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
    target_size: int,
    min_size: int,
    generator_version: str,
    quiz_pool_enabled: bool,
) -> int:
    if not db_path.exists():
        raise RuntimeError(f"db_not_found: {db_path}")

    run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    start_ts = utc_now_iso()
    logger = QuizPoolLogger(log_dir)

    processed = 0
    generated = 0
    available = 0
    not_available = 0
    skipped_unchanged = 0
    total_latency_ms = 0
    error_class = ""

    conn = connect_db(db_path)
    ensure_schema(conn)

    try:
        candidates = fetch_quiz_pool_candidates(conn, limit=max_stories)
        now_ts = utc_now_iso()

        if not quiz_pool_enabled:
            for story in candidates:
                processed += 1
                not_available += 1
                update_story_quiz_state(
                    conn,
                    story_id=story["story_id"],
                    quiz_status="quiz_not_available",
                    quiz_unavailable_reason=REASON_QUIZ_TEMP_DISABLED,
                    quiz_pool_version=None,
                    quiz_updated_at=now_ts,
                )
                logger.log_reject(
                    run_id=run_id,
                    story_id=story["story_id"],
                    reason_code=REASON_QUIZ_TEMP_DISABLED,
                    details="quiz_pool_disabled_by_config",
                    latency_ms=0,
                    timestamp=now_ts,
                )

            conn.commit()
        else:
            for story in candidates:
                processed += 1
                story_id = story["story_id"]
                key_points = fetch_story_key_points_texts(conn, story_id=story_id)
                sources = fetch_story_source_links(conn, story_id=story_id)
                updated_at = utc_now_iso()

                if len(key_points) < 3 or len(sources) < 1:
                    not_available += 1
                    update_story_quiz_state(
                        conn,
                        story_id=story_id,
                        quiz_status="quiz_not_available",
                        quiz_unavailable_reason=REASON_POOL_QUALITY_FAILED,
                        quiz_pool_version=None,
                        quiz_updated_at=updated_at,
                    )
                    logger.log_reject(
                        run_id=run_id,
                        story_id=story_id,
                        reason_code=REASON_POOL_QUALITY_FAILED,
                        details="insufficient_story_inputs",
                        latency_ms=0,
                        timestamp=updated_at,
                    )
                    continue

                signature = build_pool_signature(
                    generator_version=generator_version,
                    model=model,
                    story=story,
                    key_points=key_points,
                    sources=sources,
                )

                latest = fetch_latest_quiz_metadata(conn, story_id=story_id)
                if latest and latest.get("pool_signature") == signature and latest.get("question_pool_size", 0) >= min_size:
                    skipped_unchanged += 1
                    available += 1
                    update_story_quiz_state(
                        conn,
                        story_id=story_id,
                        quiz_status="quiz_available",
                        quiz_unavailable_reason=None,
                        quiz_pool_version=int(latest["version"]),
                        quiz_updated_at=updated_at,
                    )
                    continue

                questions, reason_code, latency_ms = generate_questions_for_story(
                    story=story,
                    key_points=key_points,
                    sources=sources,
                    ollama_base_url=ollama_base_url,
                    model=model,
                    timeout_seconds=timeout_seconds,
                    max_retries=max_retries,
                    backoff_seconds=backoff_seconds,
                    target_size=target_size,
                    min_size=min_size,
                )
                total_latency_ms += latency_ms

                if questions is None:
                    not_available += 1
                    mapped_reason = reason_code or REASON_QUIZ_GENERATION_FAILED
                    update_story_quiz_state(
                        conn,
                        story_id=story_id,
                        quiz_status="quiz_not_available",
                        quiz_unavailable_reason=mapped_reason,
                        quiz_pool_version=None,
                        quiz_updated_at=updated_at,
                    )
                    logger.log_reject(
                        run_id=run_id,
                        story_id=story_id,
                        reason_code=mapped_reason,
                        details="generation_or_validation_failed",
                        latency_ms=latency_ms,
                        timestamp=updated_at,
                    )
                    continue

                next_version = (int(latest["version"]) + 1) if latest else 1
                quiz_id = build_quiz_id(story_id, next_version)
                created_at = utc_now_iso()
                persisted_questions = attach_question_ids(quiz_id, questions)

                insert_quiz(
                    conn,
                    quiz_id=quiz_id,
                    story_id=story_id,
                    version=next_version,
                    question_pool_size=len(persisted_questions),
                    pool_signature=signature,
                    generator_version=generator_version,
                    created_at=created_at,
                )
                insert_quiz_questions(
                    conn,
                    quiz_id=quiz_id,
                    questions=persisted_questions,
                    created_at=created_at,
                )
                update_story_quiz_state(
                    conn,
                    story_id=story_id,
                    quiz_status="quiz_available",
                    quiz_unavailable_reason=None,
                    quiz_pool_version=next_version,
                    quiz_updated_at=created_at,
                )

                generated += 1
                available += 1

            conn.commit()
    except Exception as exc:  # noqa: BLE001
        conn.rollback()
        error_class = f"runtime_error:{type(exc).__name__}"
        raise
    finally:
        publishable_total = count_publishable_stories(conn)
        quiz_available_total = count_quiz_available_stories(conn)
        coverage_percent = (quiz_available_total / publishable_total * 100.0) if publishable_total else 0.0
        end_ts = utc_now_iso()
        avg_latency_ms = int(total_latency_ms / generated) if generated else 0
        logger.log_run(
            run_id=run_id,
            start_ts=start_ts,
            end_ts=end_ts,
            processed=processed,
            generated=generated,
            available=available,
            not_available=not_available,
            skipped_unchanged=skipped_unchanged,
            coverage_percent=coverage_percent,
            avg_latency_ms=avg_latency_ms,
            error_class=error_class,
        )
        conn.close()

    print(
        "[QUIZ_POOL_SUMMARY] "
        f"run_id={run_id} processed={processed} generated={generated} available={available} "
        f"not_available={not_available} skipped_unchanged={skipped_unchanged}"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poli-News quiz pool generator (W2-05)")
    parser.add_argument("--run-once", action="store_true", help="Generate quiz pools once")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--ollama-base-url", type=str, default=OLLAMA_BASE_URL)
    parser.add_argument("--model", type=str, default=QUIZ_POOL_MODEL or KEYPOINTS_MODEL)
    parser.add_argument("--timeout-seconds", type=int, default=QUIZ_POOL_TIMEOUT_SECONDS)
    parser.add_argument("--max-retries", type=int, default=QUIZ_POOL_MAX_RETRIES)
    parser.add_argument(
        "--backoff-seconds",
        type=str,
        default=",".join(str(i) for i in QUIZ_POOL_BACKOFF_SECONDS),
        help="Comma-separated backoff seconds, e.g. 1,3",
    )
    parser.add_argument("--max-stories", type=int, default=QUIZ_POOL_MAX_STORIES_PER_RUN)
    parser.add_argument("--target-size", type=int, default=QUIZ_POOL_TARGET_SIZE)
    parser.add_argument("--min-size", type=int, default=QUIZ_POOL_MIN_SIZE)
    parser.add_argument("--generator-version", type=str, default=QUIZ_POOL_GENERATOR_VERSION)
    parser.add_argument(
        "--disable-pool",
        action="store_true",
        help="Force quiz_temporarily_disabled status regardless of provider availability",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.run_once:
        print("Error: only --run-once mode is supported in W2-05.", file=sys.stderr)
        return 1

    quiz_pool_enabled = QUIZ_POOL_ENABLED and not args.disable_pool
    if args.min_size < 1:
        print("Error: --min-size must be >= 1", file=sys.stderr)
        return 1
    if args.target_size < args.min_size:
        print("Error: --target-size must be >= --min-size", file=sys.stderr)
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
            target_size=args.target_size,
            min_size=args.min_size,
            generator_version=args.generator_version,
            quiz_pool_enabled=quiz_pool_enabled,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"[QUIZ_POOL_ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
