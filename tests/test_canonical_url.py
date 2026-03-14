from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.error import URLError

from collector.canonical_url import normalize_canonical_url, resolve_canonical_url


class _FakeResponse:
    def __init__(self, final_url: str) -> None:
        self._final_url = final_url

    def geturl(self) -> str:
        return self._final_url

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class TestCanonicalUrl(unittest.TestCase):
    def test_normalize_canonical_url(self) -> None:
        raw = "HTTPS://Example.com/news?id=1&utm_source=gn&fbclid=x#section"
        self.assertEqual(normalize_canonical_url(raw), "https://example.com/news?id=1")

    def test_resolve_direct_non_google(self) -> None:
        canonical, mode, err = resolve_canonical_url(
            "https://example.com/article?utm_source=foo",
            "https://example.com",
            max_retries=0,
            backoff_seconds=(),
        )
        self.assertEqual(canonical, "https://example.com/article")
        self.assertEqual(mode, "resolved_direct")
        self.assertEqual(err, "")

    def test_resolve_google_redirect_success(self) -> None:
        with patch("collector.canonical_url.urlopen", return_value=_FakeResponse("https://publisher.com/p/123?utm_source=x")):
            canonical, mode, err = resolve_canonical_url(
                "https://news.google.com/rss/articles/CBMi...",
                "https://publisher.com",
                max_retries=0,
                backoff_seconds=(),
            )
        self.assertEqual(canonical, "https://publisher.com/p/123")
        self.assertEqual(mode, "resolved_redirect")
        self.assertEqual(err, "")

    def test_resolve_google_redirect_failure_fallback(self) -> None:
        with patch("collector.canonical_url.urlopen", side_effect=URLError("network")):
            canonical, mode, err = resolve_canonical_url(
                "https://news.google.com/rss/articles/CBMi...",
                "https://publisher.com",
                max_retries=0,
                backoff_seconds=(),
            )
        self.assertEqual(canonical, "https://publisher.com")
        self.assertEqual(mode, "fallback_source")
        self.assertEqual(err, "")

    def test_resolve_google_unresolved_google_final_fallback(self) -> None:
        with patch("collector.canonical_url.urlopen", return_value=_FakeResponse("https://news.google.com/articles/CBMi...")):
            canonical, mode, err = resolve_canonical_url(
                "https://news.google.com/rss/articles/CBMi...",
                "https://publisher.com",
                max_retries=0,
                backoff_seconds=(),
            )
        self.assertEqual(canonical, "https://publisher.com")
        self.assertEqual(mode, "fallback_source")
        self.assertEqual(err, "")

    def test_resolve_error_when_both_invalid(self) -> None:
        canonical, mode, err = resolve_canonical_url(
            "not-a-url",
            "also-not-url",
            max_retries=0,
            backoff_seconds=(),
        )
        self.assertIsNone(canonical)
        self.assertEqual(mode, "error")
        self.assertEqual(err, "invalid_canonical_url")


if __name__ == "__main__":
    unittest.main()
