from __future__ import annotations

import sqlite3
import unittest

from collector.dedup import build_dedup_key, build_title_fingerprint, is_duplicate


class TestDedup(unittest.TestCase):
    def test_title_fingerprint_normalization(self) -> None:
        a = build_title_fingerprint("Breaking: Market Rally!!!")
        b = build_title_fingerprint("breaking market rally")
        self.assertEqual(a, b)

    def test_same_story_same_bucket_same_key(self) -> None:
        title_fp = build_title_fingerprint("Fed keeps rates unchanged")
        k1 = build_dedup_key(
            title_fingerprint=title_fp,
            publisher_domain="example.com",
            url_normalized="https://example.com/news/fed",
            published_at_iso="2026-03-14T10:00:00+00:00",
            window_hours=24,
        )
        k2 = build_dedup_key(
            title_fingerprint=title_fp,
            publisher_domain="example.com",
            url_normalized="https://example.com/news/fed",
            published_at_iso="2026-03-14T20:59:00+00:00",
            window_hours=24,
        )
        self.assertEqual(k1, k2)

    def test_different_story_different_key(self) -> None:
        k1 = build_dedup_key(
            title_fingerprint=build_title_fingerprint("Story A"),
            publisher_domain="example.com",
            url_normalized="https://example.com/a",
            published_at_iso="2026-03-14T10:00:00+00:00",
            window_hours=24,
        )
        k2 = build_dedup_key(
            title_fingerprint=build_title_fingerprint("Story B"),
            publisher_domain="example.com",
            url_normalized="https://example.com/b",
            published_at_iso="2026-03-14T10:00:00+00:00",
            window_hours=24,
        )
        self.assertNotEqual(k1, k2)

    def test_same_story_different_bucket_different_key(self) -> None:
        title_fp = build_title_fingerprint("Same story")
        k1 = build_dedup_key(
            title_fingerprint=title_fp,
            publisher_domain="example.com",
            url_normalized="https://example.com/same",
            published_at_iso="2026-03-14T10:00:00+00:00",
            window_hours=24,
        )
        k2 = build_dedup_key(
            title_fingerprint=title_fp,
            publisher_domain="example.com",
            url_normalized="https://example.com/same",
            published_at_iso="2026-03-15T10:00:00+00:00",
            window_hours=24,
        )
        self.assertNotEqual(k1, k2)

    def test_is_duplicate(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE TABLE dedup_registry (dedup_key TEXT PRIMARY KEY, story_id TEXT, raw_id TEXT, created_at TEXT)")
        conn.execute(
            "INSERT INTO dedup_registry (dedup_key, story_id, raw_id, created_at) VALUES (?, ?, ?, ?)",
            ("dedup_abc", "story_1", "raw_1", "2026-03-14T00:00:00+00:00"),
        )
        conn.commit()

        self.assertTrue(is_duplicate(conn, "dedup_abc"))
        self.assertFalse(is_duplicate(conn, "dedup_missing"))


if __name__ == "__main__":
    unittest.main()
