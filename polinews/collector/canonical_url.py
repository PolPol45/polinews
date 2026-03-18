from __future__ import annotations

import time
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from polinews.collector.config import (
    CANONICAL_RESOLVE_BACKOFF_SECONDS,
    CANONICAL_RESOLVE_MAX_RETRIES,
    CANONICAL_RESOLVE_TIMEOUT_SECONDS,
    USER_AGENT,
)

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "igshid",
    "ref",
    "ref_src",
}

GOOGLE_NEWS_HOSTS = {"news.google.com"}


def normalize_canonical_url(url: str | None) -> str | None:
    if not url:
        return None

    try:
        parsed = urlsplit(url.strip())
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None

    host = parsed.netloc.lower()
    filtered_params: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        key_lower = key.lower()
        if key_lower.startswith("utm_"):
            continue
        if key_lower in TRACKING_QUERY_KEYS:
            continue
        filtered_params.append((key, value))

    query = urlencode(filtered_params, doseq=True)
    normalized = urlunsplit((scheme, host, parsed.path or "", query, ""))
    return normalized


def is_google_news_url(url: str | None) -> bool:
    normalized = normalize_canonical_url(url)
    if not normalized:
        return False
    host = urlsplit(normalized).netloc
    return host in GOOGLE_NEWS_HOSTS


def resolve_canonical_url(
    raw_link: str | None,
    source_url: str | None,
    *,
    timeout_seconds: int = CANONICAL_RESOLVE_TIMEOUT_SECONDS,
    max_retries: int = CANONICAL_RESOLVE_MAX_RETRIES,
    backoff_seconds: Iterable[int] = CANONICAL_RESOLVE_BACKOFF_SECONDS,
    user_agent: str = USER_AGENT,
) -> tuple[str | None, str, str]:
    normalized_source = normalize_canonical_url(source_url)
    normalized_raw = normalize_canonical_url(raw_link)
    if not normalized_raw:
        if normalized_source:
            return normalized_source, "fallback_source", ""
        return None, "error", "invalid_canonical_url"

    if not is_google_news_url(normalized_raw):
        return normalized_raw, "resolved_direct", ""

    final_url = _resolve_redirect_url(
        normalized_raw,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        backoff_seconds=tuple(backoff_seconds),
        user_agent=user_agent,
    )
    normalized_final = normalize_canonical_url(final_url)
    if normalized_final and not is_google_news_url(normalized_final):
        return normalized_final, "resolved_redirect", ""

    if normalized_source:
        return normalized_source, "fallback_source", ""
    return None, "error", "invalid_canonical_url"


def _resolve_redirect_url(
    url: str,
    *,
    timeout_seconds: int,
    max_retries: int,
    backoff_seconds: tuple[int, ...],
    user_agent: str,
) -> str | None:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            req = Request(url, headers={"User-Agent": user_agent})
            with urlopen(req, timeout=timeout_seconds) as response:
                return response.geturl()
        except (URLError, HTTPError, TimeoutError, ValueError) as exc:
            last_error = exc
            if attempt < max_retries:
                if backoff_seconds:
                    backoff = backoff_seconds[min(attempt, len(backoff_seconds) - 1)]
                    time.sleep(backoff)
    _ = last_error
    return None
