from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

from collector.db import (
    connect_db,
    ensure_schema,
    insert_story,
    insert_story_source,
)
from collector.keypoints_generator import (
    call_ollama,
    parse_key_points_payload,
    run_once,
    validate_key_points,
)


class _FakeResponse:
    def __init__(self, payload: str) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return self._payload.encode("utf-8")

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:  # noqa: ANN001
        return False


class TestKeypointsGenerator(unittest.TestCase):
    def test_parse_key_points_payload_valid(self) -> None:
        points, error = parse_key_points_payload('{"key_points": ["A", "B", "C"]}')
        self.assertEqual(points, ["A", "B", "C"])
        self.assertEqual(error, "")

    def test_parse_key_points_payload_invalid(self) -> None:
        points, error = parse_key_points_payload("not-json")
        self.assertIsNone(points)
        self.assertEqual(error, "keypoints_invalid_json")

    def test_validate_key_points_rules(self) -> None:
        valid, err = validate_key_points(["Uno", "Due", "Tre"])
        self.assertEqual(valid, ["Uno", "Due", "Tre"])
        self.assertEqual(err, "")

        invalid, err = validate_key_points(["Uno", "Uno", "Tre"])
        self.assertIsNone(invalid)
        self.assertEqual(err, "keypoints_duplicates")

        invalid, err = validate_key_points(["Solo due", "punti"])
        self.assertIsNone(invalid)
        self.assertEqual(err, "keypoints_invalid_count")

    def test_call_ollama_network_failure(self) -> None:
        with patch("collector.keypoints_generator.urlopen", side_effect=URLError("down")):
            payload, err = call_ollama(
                base_url="http://localhost:11434",
                model="qwen2.5:3b",
                prompt="x",
                timeout_seconds=1,
                max_retries=0,
                backoff_seconds=(),
            )
        self.assertIsNone(payload)
        self.assertEqual(err, "keypoints_generation_failed")

    def test_call_ollama_success(self) -> None:
        with patch(
            "collector.keypoints_generator.urlopen",
            return_value=_FakeResponse('{"response": "{\\"key_points\\":[\\"A\\",\\"B\\",\\"C\\"]}"}'),
        ):
            payload, err = call_ollama(
                base_url="http://localhost:11434",
                model="qwen2.5:3b",
                prompt="x",
                timeout_seconds=1,
                max_retries=0,
                backoff_seconds=(),
            )
        self.assertEqual(payload, '{"key_points":["A","B","C"]}')
        self.assertEqual(err, "")

    def test_run_once_sets_publishable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_path = tmp / "polinews.db"
            log_dir = tmp / "logs"

            conn = connect_db(db_path)
            ensure_schema(conn)
            insert_story(
                conn,
                story_id="story_1",
                topic_slug="politics",
                headline="Headline",
                summary="Summary",
                published_at="2026-03-14T10:00:00+00:00",
                source_count=1,
                created_at="2026-03-14T10:01:00+00:00",
            )
            insert_story_source(
                conn,
                story_source_id="ss_1",
                story_id="story_1",
                source_name="Reuters",
                source_url="https://reuters.com/x",
                canonical_url="https://reuters.com/x",
                publisher_domain="reuters.com",
            )
            conn.commit()
            conn.close()

            with patch(
                "collector.keypoints_generator.generate_key_points",
                return_value=(["Punto 1", "Punto 2", "Punto 3"], "", 15),
            ):
                exit_code = run_once(
                    db_path=db_path,
                    log_dir=log_dir,
                    ollama_base_url="http://localhost:11434",
                    model="qwen2.5:3b",
                    timeout_seconds=1,
                    max_retries=0,
                    backoff_seconds=(),
                    max_stories=10,
                )
            self.assertEqual(exit_code, 0)

            verify = sqlite3.connect(db_path)
            story_row = verify.execute(
                "SELECT status, publishability_reason FROM stories WHERE story_id = 'story_1'"
            ).fetchone()
            kp_count = verify.execute(
                "SELECT COUNT(*) FROM story_key_points WHERE story_id = 'story_1'"
            ).fetchone()[0]
            verify.close()

            self.assertEqual(story_row[0], "publishable")
            self.assertIsNone(story_row[1])
            self.assertEqual(kp_count, 3)

    def test_run_once_keeps_not_publishable_on_invalid_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_path = tmp / "polinews.db"
            log_dir = tmp / "logs"

            conn = connect_db(db_path)
            ensure_schema(conn)
            insert_story(
                conn,
                story_id="story_2",
                topic_slug="world",
                headline="Headline",
                summary="Summary",
                published_at="2026-03-14T10:00:00+00:00",
                source_count=1,
                created_at="2026-03-14T10:01:00+00:00",
            )
            insert_story_source(
                conn,
                story_source_id="ss_2",
                story_id="story_2",
                source_name="BBC",
                source_url="https://bbc.com/x",
                canonical_url="https://bbc.com/x",
                publisher_domain="bbc.com",
            )
            conn.commit()
            conn.close()

            with patch(
                "collector.keypoints_generator.generate_key_points",
                return_value=(None, "keypoints_invalid_count", 12),
            ):
                run_once(
                    db_path=db_path,
                    log_dir=log_dir,
                    ollama_base_url="http://localhost:11434",
                    model="qwen2.5:3b",
                    timeout_seconds=1,
                    max_retries=0,
                    backoff_seconds=(),
                    max_stories=10,
                )

            verify = sqlite3.connect(db_path)
            story_row = verify.execute(
                "SELECT status, publishability_reason FROM stories WHERE story_id = 'story_2'"
            ).fetchone()
            kp_count = verify.execute(
                "SELECT COUNT(*) FROM story_key_points WHERE story_id = 'story_2'"
            ).fetchone()[0]
            verify.close()

            self.assertEqual(story_row[0], "not_publishable")
            self.assertEqual(story_row[1], "keypoints_invalid_count")
            self.assertEqual(kp_count, 0)


if __name__ == "__main__":
    unittest.main()
