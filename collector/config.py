from pathlib import Path

REQUEST_TIMEOUT_SECONDS = 8
MAX_RETRIES = 3
BACKOFF_SECONDS = (1, 3, 9)
USER_AGENT = "PoliNewsMVPFeedCollector/1.0"
STALE_THRESHOLD = 3
DEDUP_WINDOW_HOURS = 24

DEFAULT_FEEDS_CSV = Path("docs/mvp_offchain/specs/feed_registry_v1.csv")
DEFAULT_DB_PATH = Path("data/polinews.db")
DEFAULT_LOG_DIR = Path("logs")
DEFAULT_STATE_PATH = Path("data/stale_state.json")
