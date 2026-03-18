"""
Scheduler worker — APScheduler-based pipeline orchestration.

Runs the full ingestion chain every COLLECTOR_INTERVAL_MINUTES:
  collect → normalize → keypoints_gen → quiz_pool_gen
"""
from __future__ import annotations

import logging
import random
import time
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.schedulers.background import BackgroundScheduler

from polinews.config import (
    CANONICAL_RESOLVE_BACKOFF_SECONDS,
    CANONICAL_RESOLVE_MAX_RETRIES,
    CANONICAL_RESOLVE_TIMEOUT_SECONDS,
    COLLECTOR_INTERVAL_MINUTES,
    COLLECTOR_JITTER_SECONDS,
    DB_PATH,
    DEDUP_WINDOW_HOURS,
    DEFAULT_FEEDS_CSV,
    DEFAULT_LOG_DIR,
    DEFAULT_STATE_PATH,
    KEYPOINTS_BACKOFF_SECONDS,
    KEYPOINTS_MAX_RETRIES,
    KEYPOINTS_MAX_STORIES_PER_RUN,
    KEYPOINTS_MODEL,
    KEYPOINTS_TIMEOUT_SECONDS,
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
)

log = logging.getLogger("polinews.worker")


DEFAULT_TOPICS_FILE = Path("docs/mvp_offchain/specs/topics_v1.md")


def _run_collect() -> None:
    from polinews.collector.rss_collector import run_once as collect_once
    log.info("[worker] collect: start")
    t0 = time.perf_counter()
    try:
        collect_once(
            feeds_csv=DEFAULT_FEEDS_CSV,
            db_path=DB_PATH,
            log_dir=DEFAULT_LOG_DIR,
            state_path=DEFAULT_STATE_PATH,
        )
        log.info("[worker] collect: done in %.1fs", time.perf_counter() - t0)
    except Exception:
        log.exception("[worker] collect: FAILED")


def _run_normalize() -> None:
    from polinews.collector.normalizer import run_once as normalize_once
    log.info("[worker] normalize: start")
    t0 = time.perf_counter()
    try:
        normalize_once(
            db_path=DB_PATH,
            feeds_csv=DEFAULT_FEEDS_CSV,
            topics_file=DEFAULT_TOPICS_FILE,
            log_dir=DEFAULT_LOG_DIR,
            dedup_window_hours=DEDUP_WINDOW_HOURS,
            canonical_timeout_seconds=CANONICAL_RESOLVE_TIMEOUT_SECONDS,
            canonical_max_retries=CANONICAL_RESOLVE_MAX_RETRIES,
            canonical_backoff_seconds=CANONICAL_RESOLVE_BACKOFF_SECONDS,
        )
        log.info("[worker] normalize: done in %.1fs", time.perf_counter() - t0)
    except Exception:
        log.exception("[worker] normalize: FAILED")


def _run_keypoints() -> None:
    from polinews.collector.keypoints_generator import run_once as keypoints_once
    log.info("[worker] keypoints: start")
    t0 = time.perf_counter()
    try:
        keypoints_once(
            db_path=DB_PATH,
            log_dir=DEFAULT_LOG_DIR,
            ollama_base_url=OLLAMA_BASE_URL,
            model=KEYPOINTS_MODEL,
            timeout_seconds=KEYPOINTS_TIMEOUT_SECONDS,
            max_retries=KEYPOINTS_MAX_RETRIES,
            backoff_seconds=KEYPOINTS_BACKOFF_SECONDS,
            max_stories=KEYPOINTS_MAX_STORIES_PER_RUN,
        )
        log.info("[worker] keypoints: done in %.1fs", time.perf_counter() - t0)
    except Exception:
        log.exception("[worker] keypoints: FAILED")


def _run_quiz_pool() -> None:
    from polinews.collector.quiz_pool_generator import run_once as quiz_once
    log.info("[worker] quiz_pool: start")
    t0 = time.perf_counter()
    try:
        quiz_once(
            db_path=DB_PATH,
            log_dir=DEFAULT_LOG_DIR,
            ollama_base_url=OLLAMA_BASE_URL,
            model=QUIZ_POOL_MODEL,
            timeout_seconds=QUIZ_POOL_TIMEOUT_SECONDS,
            max_retries=QUIZ_POOL_MAX_RETRIES,
            backoff_seconds=QUIZ_POOL_BACKOFF_SECONDS,
            max_stories=QUIZ_POOL_MAX_STORIES_PER_RUN,
            target_size=QUIZ_POOL_TARGET_SIZE,
            min_size=QUIZ_POOL_MIN_SIZE,
            generator_version=QUIZ_POOL_GENERATOR_VERSION,
            quiz_pool_enabled=QUIZ_POOL_ENABLED,
        )
        log.info("[worker] quiz_pool: done in %.1fs", time.perf_counter() - t0)
    except Exception:
        log.exception("[worker] quiz_pool: FAILED")


def run_pipeline_once() -> None:
    """Execute the full ingestion pipeline once (collect → normalize → keypoints → quiz → analytics)."""
    jitter = random.randint(0, COLLECTOR_JITTER_SECONDS)
    if jitter > 0:
        log.info("[worker] sleeping %ds jitter", jitter)
        time.sleep(jitter)
    _run_collect()
    _run_normalize()
    _run_keypoints()
    _run_quiz_pool()
    
    from polinews.worker.analytics_job import run_analytics_once
    run_analytics_once()


def start_blocking_scheduler() -> None:
    """Start the scheduler and block the process (use for polinews-collect entry point)."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    log.info("[worker] starting blocking scheduler — interval=%dm", COLLECTOR_INTERVAL_MINUTES)

    # Run immediately on startup
    run_pipeline_once()

    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_pipeline_once,
        "interval",
        minutes=COLLECTOR_INTERVAL_MINUTES,
        id="pipeline",
        max_instances=1,
        coalesce=True,
    )
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("[worker] scheduler stopped")


def make_background_scheduler() -> BackgroundScheduler:
    """
    Return a BackgroundScheduler (not yet started).
    Used when embedding the scheduler inside the API process.
    """
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline_once,
        "interval",
        minutes=COLLECTOR_INTERVAL_MINUTES,
        id="pipeline",
        max_instances=1,
        coalesce=True,
    )
    return scheduler
