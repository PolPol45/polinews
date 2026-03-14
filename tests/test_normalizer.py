from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from collector.normalizer import (
    clean_text,
    deterministic_story_id,
    deterministic_story_source_id,
    extract_snippet,
    load_feed_topic_map,
    load_topic_slugs,
    normalize_url,
    parse_datetime_utc,
)


class TestNormalizerUtils(unittest.TestCase):
    def test_clean_text_html_and_spaces(self) -> None:
        value = "  Breaking&nbsp;News <b>Now</b>  "
        self.assertEqual(clean_text(value), "Breaking News Now")

    def test_clean_text_empty(self) -> None:
        self.assertIsNone(clean_text("   \n\t  "))

    def test_normalize_url_removes_tracking_params(self) -> None:
        url = "https://Example.com/path?a=1&utm_source=google&fbclid=abc#frag"
        self.assertEqual(normalize_url(url), "https://example.com/path?a=1")

    def test_normalize_url_invalid(self) -> None:
        self.assertIsNone(normalize_url("not-a-url"))
        self.assertIsNone(normalize_url("ftp://example.com/file"))

    def test_parse_datetime_rfc822(self) -> None:
        value = "Sat, 14 Mar 2026 10:00:00 GMT"
        parsed = parse_datetime_utc(value)
        self.assertIsNotNone(parsed)
        self.assertTrue(parsed.endswith("+00:00"))

    def test_parse_datetime_iso(self) -> None:
        value = "2026-03-14T10:00:00Z"
        parsed = parse_datetime_utc(value)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed, "2026-03-14T10:00:00+00:00")

    def test_deterministic_story_ids(self) -> None:
        raw_id = "abc-123"
        self.assertEqual(deterministic_story_id(raw_id), deterministic_story_id(raw_id))
        sid = deterministic_story_id(raw_id)
        self.assertTrue(sid.startswith("story_"))
        ssid = deterministic_story_source_id(sid, "https://example.com/a")
        self.assertTrue(ssid.startswith("ss_"))

    def test_extract_snippet_fallback_from_payload(self) -> None:
        snippet = extract_snippet(None, {"description": "  <p>Payload&nbsp;snippet</p> "})
        self.assertEqual(snippet, "Payload snippet")

    def test_topic_mapping_and_topics_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            topics_file = tmp / "topics.md"
            feeds_file = tmp / "feeds.csv"

            topics_file.write_text(
                "\n".join(
                    [
                        "| Topic | Slug | Description |",
                        "|---|---|---|",
                        "| Politics | politics | test |",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            feeds_file.write_text(
                "\n".join(
                    [
                        "feed_id,topic_slug,locale,hl,gl,ceid,url,status,notes",
                        "feed_politics_us,politics,en-US,hl=en-US,gl=US,US:en,https://example.com/rss,active,primary",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            topics = load_topic_slugs(topics_file)
            feed_map = load_feed_topic_map(feeds_file)

            self.assertEqual(topics, {"politics"})
            self.assertEqual(feed_map["feed_politics_us"], "politics")


if __name__ == "__main__":
    unittest.main()
