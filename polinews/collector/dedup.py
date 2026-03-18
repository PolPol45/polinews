from __future__ import annotations

"""W1-07 dedup rules.

Versioned rule:
- DEDUP_RULE_VERSION = w1-07-v1
- reason_code = duplicate_story
- dedup_key = sha1(title_fingerprint + publisher_domain + url_normalized + time_bucket)
"""

import hashlib
import re
from datetime import datetime, timezone

DEDUP_RULE_VERSION = "w1-07-v1"
DEDUP_REASON_CODE = "duplicate_story"


def build_title_fingerprint(title: str) -> str:
    lowered = title.lower().strip()
    normalized = re.sub(r"[^a-z0-9\s]", " ", lowered)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def _bucket_start_iso(published_at_iso: str, window_hours: int) -> str:
    parsed = datetime.fromisoformat(published_at_iso.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    dt_utc = parsed.astimezone(timezone.utc)

    epoch_hours = int(dt_utc.timestamp() // 3600)
    bucket_hours = (epoch_hours // window_hours) * window_hours
    bucket_start = datetime.fromtimestamp(bucket_hours * 3600, tz=timezone.utc)
    return bucket_start.isoformat()


def build_dedup_key(
    title_fingerprint: str,
    publisher_domain: str,
    url_normalized: str,
    published_at_iso: str,
    window_hours: int,
) -> str:
    time_bucket = _bucket_start_iso(published_at_iso, window_hours)
    canonical = "|".join(
        [
            title_fingerprint,
            publisher_domain.lower().strip(),
            url_normalized.strip(),
            time_bucket,
        ]
    )
    digest = hashlib.sha1(canonical.encode("utf-8")).hexdigest()  # noqa: S324
    return f"dedup_{digest}"


def is_duplicate(conn, dedup_key: str) -> bool:
    row = conn.execute("SELECT 1 FROM dedup_registry WHERE dedup_key = ? LIMIT 1", (dedup_key,)).fetchone()
    return row is not None
