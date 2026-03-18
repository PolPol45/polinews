"""Poli-News unified configuration — reads from environment / .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from repo root if it exists (no-op in production)
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _csv_ints(key: str, default: tuple[int, ...]) -> tuple[int, ...]:
    raw = os.getenv(key, "")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    try:
        return tuple(int(p) for p in parts) if parts else default
    except ValueError:
        return default


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def _bool(key: str, default: bool) -> bool:
    return os.getenv(key, "1" if default else "0") == "1"


# ── Database ──────────────────────────────────────────────────────────────────
DB_PATH = Path(os.getenv("POLINEWS_DB_PATH", "data/polinews.db"))

# ── Auth ──────────────────────────────────────────────────────────────────────
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev_secret_change_in_production")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_DAYS: int = _int("JWT_EXPIRE_DAYS", 7)

MAGIC_LINK_EXPIRE_MINUTES: int = _int("MAGIC_LINK_EXPIRE_MINUTES", 15)
# "log" → print to stdout (dev) | "resend" → send via Resend API
MAGIC_LINK_DELIVERY: str = os.getenv("MAGIC_LINK_DELIVERY", "log")
RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL: str = os.getenv("RESEND_FROM_EMAIL", "noreply@polinews.io")

# ── LLM provider ──────────────────────────────────────────────────────────────
# "ollama" | "openai"
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
KEYPOINTS_MODEL: str = os.getenv("KEYPOINTS_MODEL", "qwen2.5:3b")
QUIZ_POOL_MODEL: str = os.getenv("QUIZ_POOL_MODEL", KEYPOINTS_MODEL)

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_KEYPOINTS_MODEL: str = os.getenv("OPENAI_KEYPOINTS_MODEL", "gpt-4o-mini")
OPENAI_QUIZ_MODEL: str = os.getenv("OPENAI_QUIZ_MODEL", "gpt-4o-mini")

# ── Ingestion ─────────────────────────────────────────────────────────────────
DEFAULT_FEEDS_CSV = Path(os.getenv("DEFAULT_FEEDS_CSV", "docs/mvp_offchain/specs/feed_registry_v1.csv"))
DEFAULT_LOG_DIR = Path(os.getenv("DEFAULT_LOG_DIR", "logs"))
DEFAULT_STATE_PATH = Path(os.getenv("DEFAULT_STATE_PATH", "data/stale_state.json"))

USER_AGENT: str = "PoliNewsMVPFeedCollector/1.0"
REQUEST_TIMEOUT_SECONDS: int = _int("REQUEST_TIMEOUT_SECONDS", 8)
MAX_RETRIES: int = _int("MAX_RETRIES", 3)
BACKOFF_SECONDS: tuple[int, ...] = _csv_ints("BACKOFF_SECONDS", (1, 3, 9))
STALE_THRESHOLD: int = _int("STALE_THRESHOLD", 3)
DEDUP_WINDOW_HOURS: int = _int("DEDUP_WINDOW_HOURS", 24)

CANONICAL_RESOLVE_TIMEOUT_SECONDS: int = REQUEST_TIMEOUT_SECONDS
CANONICAL_RESOLVE_MAX_RETRIES: int = MAX_RETRIES
CANONICAL_RESOLVE_BACKOFF_SECONDS: tuple[int, ...] = BACKOFF_SECONDS

KEYPOINTS_TIMEOUT_SECONDS: int = _int("KEYPOINTS_TIMEOUT_SECONDS", 25)
KEYPOINTS_MAX_RETRIES: int = _int("KEYPOINTS_MAX_RETRIES", 2)
KEYPOINTS_BACKOFF_SECONDS: tuple[int, ...] = _csv_ints("KEYPOINTS_BACKOFF_SECONDS", (1, 3))
KEYPOINTS_MAX_STORIES_PER_RUN: int = _int("KEYPOINTS_MAX_STORIES_PER_RUN", 150)

QUIZ_POOL_ENABLED: bool = _bool("QUIZ_POOL_ENABLED", True)
QUIZ_POOL_TIMEOUT_SECONDS: int = _int("QUIZ_POOL_TIMEOUT_SECONDS", 30)
QUIZ_POOL_MAX_RETRIES: int = _int("QUIZ_POOL_MAX_RETRIES", 2)
QUIZ_POOL_BACKOFF_SECONDS: tuple[int, ...] = _csv_ints("QUIZ_POOL_BACKOFF_SECONDS", (1, 3))
QUIZ_POOL_MAX_STORIES_PER_RUN: int = _int("QUIZ_POOL_MAX_STORIES_PER_RUN", 150)
QUIZ_POOL_TARGET_SIZE: int = _int("QUIZ_POOL_TARGET_SIZE", 10)
QUIZ_POOL_MIN_SIZE: int = _int("QUIZ_POOL_MIN_SIZE", 4)
QUIZ_POOL_GENERATOR_VERSION: str = os.getenv("QUIZ_POOL_GENERATOR_VERSION", "v1")

# ── Scheduler ─────────────────────────────────────────────────────────────────
COLLECTOR_INTERVAL_MINUTES: int = _int("COLLECTOR_INTERVAL_MINUTES", 15)
COLLECTOR_JITTER_SECONDS: int = _int("COLLECTOR_JITTER_SECONDS", 30)

# ── API server ────────────────────────────────────────────────────────────────
API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
API_PORT: int = _int("API_PORT", 8000)
CORS_ORIGINS: list[str] = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

# ── Publisher auth ────────────────────────────────────────────────────────────
PUBLISHER_API_KEY: str = os.getenv("PUBLISHER_API_KEY", "dev_publisher_key")

# ── Rate limiting ─────────────────────────────────────────────────────────────
RATE_LIMIT_DEFAULT: str = os.getenv("RATE_LIMIT_DEFAULT", "60/minute")
RATE_LIMIT_ATTEMPT: str = os.getenv("RATE_LIMIT_ATTEMPT", "10/minute")

# ── Legacy aliases — keep collector/* imports working ─────────────────────────
DEFAULT_DB_PATH = DB_PATH
