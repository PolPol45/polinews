import os
from pathlib import Path


def _parse_csv_ints(value: str, default: tuple[int, ...]) -> tuple[int, ...]:
    chunks = [chunk.strip() for chunk in value.split(",") if chunk.strip()]
    if not chunks:
        return default
    return tuple(int(chunk) for chunk in chunks)

REQUEST_TIMEOUT_SECONDS = 8
MAX_RETRIES = 3
BACKOFF_SECONDS = (1, 3, 9)
USER_AGENT = "PoliNewsMVPFeedCollector/1.0"
STALE_THRESHOLD = 3
DEDUP_WINDOW_HOURS = 24
CANONICAL_RESOLVE_TIMEOUT_SECONDS = REQUEST_TIMEOUT_SECONDS
CANONICAL_RESOLVE_MAX_RETRIES = MAX_RETRIES
CANONICAL_RESOLVE_BACKOFF_SECONDS = BACKOFF_SECONDS
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
KEYPOINTS_MODEL = os.getenv("KEYPOINTS_MODEL", "qwen2.5:3b")
KEYPOINTS_TIMEOUT_SECONDS = int(os.getenv("KEYPOINTS_TIMEOUT_SECONDS", "25"))
KEYPOINTS_MAX_RETRIES = int(os.getenv("KEYPOINTS_MAX_RETRIES", "2"))
KEYPOINTS_BACKOFF_SECONDS = _parse_csv_ints(
    os.getenv("KEYPOINTS_BACKOFF_SECONDS", "1,3"),
    default=(1, 3),
)
KEYPOINTS_MAX_STORIES_PER_RUN = int(os.getenv("KEYPOINTS_MAX_STORIES_PER_RUN", "150"))

DEFAULT_FEEDS_CSV = Path("docs/mvp_offchain/specs/feed_registry_v1.csv")
DEFAULT_DB_PATH = Path("data/polinews.db")
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_STATE_PATH = Path("data/stale_state.json")
