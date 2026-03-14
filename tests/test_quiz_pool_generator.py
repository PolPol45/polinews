from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from collector.db import (
    connect_db,
    count_quizzes_for_story,
    ensure_schema,
    fetch_latest_quiz_metadata,
    insert_story,
    insert_story_source,
    replace_story_key_points,
)
from collector.quiz_pool_generator import (
    REASON_POOL_QUALITY_FAILED,
    REASON_POOL_TOO_SMALL,
    parse_questions_payload,
    run_once,
    validate_questions,
)


def _valid_questions() -> list[dict[str, object]]:
    questions: list[dict[str, object]] = []
    for i in range(1, 5):
        task_type = "detail" if i % 2 == 0 else "comprehension"
        questions.append(
            {
                "question_text": f"Question {i}",
                "task_type": task_type,
                "options": [
                    {"option_id": "a", "text": f"A{i}"},
                    {"option_id": "b", "text": f"B{i}"},
                    {"option_id": "c", "text": f"C{i}"},
                ],
                "correct_option_id": "a",
            }
        )
    return questions


class TestQuizPoolGenerator(unittest.TestCase):
    def test_parse_questions_payload_valid(self) -> None:
        payload, err = parse_questions_payload(
            '{"questions":[{"question_text":"Q1","task_type":"comprehension","options":[{"option_id":"a","text":"x"},{"option_id":"b","text":"y"}],"correct_option_id":"a"}]}'
        )
        self.assertEqual(err, "")
        self.assertIsNotNone(payload)
        self.assertEqual(payload[0]["question_text"], "Q1")

    def test_parse_questions_payload_invalid(self) -> None:
        payload, err = parse_questions_payload("not-json")
        self.assertIsNone(payload)
        self.assertNotEqual(err, "")

    def test_validate_questions_too_small(self) -> None:
        valid, err = validate_questions(
            [
                {
                    "question_text": "Q1",
                    "task_type": "comprehension",
                    "options": [{"option_id": "a", "text": "A"}, {"option_id": "b", "text": "B"}],
                    "correct_option_id": "a",
                }
            ],
            min_size=4,
            target_size=10,
        )
        self.assertIsNone(valid)
        self.assertEqual(err, REASON_POOL_TOO_SMALL)

    def test_validate_questions_requires_mix(self) -> None:
        questions = []
        for i in range(4):
            questions.append(
                {
                    "question_text": f"Q{i}",
                    "task_type": "comprehension",
                    "options": [{"option_id": "a", "text": "A"}, {"option_id": "b", "text": "B"}],
                    "correct_option_id": "a",
                }
            )
        valid, err = validate_questions(questions, min_size=4, target_size=10)
        self.assertIsNone(valid)
        self.assertEqual(err, REASON_POOL_QUALITY_FAILED)

    def test_run_once_idempotent_and_versioned(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            db_path = tmp / "quizpool.db"
            log_dir = tmp / "logs"

            conn = connect_db(db_path)
            ensure_schema(conn)

            insert_story(
                conn,
                story_id="story_ok",
                topic_slug="world",
                headline="Headline one",
                summary="Summary one",
                published_at="2026-03-14T10:00:00+00:00",
                source_count=1,
                created_at="2026-03-14T10:01:00+00:00",
                status="publishable",
                publishability_reason=None,
                keypoints_generated_at="2026-03-14T10:02:00+00:00",
            )
            replace_story_key_points(
                conn,
                story_id="story_ok",
                key_points=["K1", "K2", "K3"],
                created_at="2026-03-14T10:02:00+00:00",
            )
            insert_story_source(
                conn,
                story_source_id="ss_ok",
                story_id="story_ok",
                source_name="Reuters",
                source_url="https://reuters.com/x",
                canonical_url="https://reuters.com/x",
                publisher_domain="reuters.com",
            )

            insert_story(
                conn,
                story_id="story_bad",
                topic_slug="health",
                headline="Headline bad",
                summary="Summary bad",
                published_at="2026-03-14T11:00:00+00:00",
                source_count=1,
                created_at="2026-03-14T11:01:00+00:00",
                status="publishable",
                publishability_reason=None,
                keypoints_generated_at="2026-03-14T11:02:00+00:00",
            )
            replace_story_key_points(
                conn,
                story_id="story_bad",
                key_points=["K1", "K2", "K3"],
                created_at="2026-03-14T11:02:00+00:00",
            )
            insert_story_source(
                conn,
                story_source_id="ss_bad",
                story_id="story_bad",
                source_name="BBC",
                source_url="https://bbc.com/x",
                canonical_url="https://bbc.com/x",
                publisher_domain="bbc.com",
            )

            conn.commit()
            conn.close()

            def _mock_generate(**kwargs):  # type: ignore[no-untyped-def]
                story = kwargs["story"]
                if story["story_id"] == "story_bad":
                    return None, REASON_POOL_TOO_SMALL, 12
                return _valid_questions(), "", 15

            with patch("collector.quiz_pool_generator.generate_questions_for_story", side_effect=_mock_generate):
                exit_code = run_once(
                    db_path=db_path,
                    log_dir=log_dir,
                    ollama_base_url="http://localhost:11434",
                    model="qwen2.5:3b",
                    timeout_seconds=1,
                    max_retries=0,
                    backoff_seconds=(),
                    max_stories=20,
                    target_size=10,
                    min_size=4,
                    generator_version="w2-05-v1",
                    quiz_pool_enabled=True,
                )
                self.assertEqual(exit_code, 0)

            verify = sqlite3.connect(db_path)
            story_ok = verify.execute(
                "SELECT quiz_status, quiz_unavailable_reason, quiz_pool_version FROM stories WHERE story_id='story_ok'"
            ).fetchone()
            story_bad = verify.execute(
                "SELECT quiz_status, quiz_unavailable_reason FROM stories WHERE story_id='story_bad'"
            ).fetchone()
            self.assertEqual(story_ok[0], "quiz_available")
            self.assertIsNone(story_ok[1])
            self.assertEqual(story_ok[2], 1)
            self.assertEqual(story_bad[0], "quiz_not_available")
            self.assertEqual(story_bad[1], REASON_POOL_TOO_SMALL)
            verify.close()

            conn = connect_db(db_path)
            ensure_schema(conn)
            self.assertEqual(count_quizzes_for_story(conn, story_id="story_ok"), 1)
            conn.close()

            # Rerun unchanged -> no new quiz version.
            with patch("collector.quiz_pool_generator.generate_questions_for_story", side_effect=_mock_generate):
                run_once(
                    db_path=db_path,
                    log_dir=log_dir,
                    ollama_base_url="http://localhost:11434",
                    model="qwen2.5:3b",
                    timeout_seconds=1,
                    max_retries=0,
                    backoff_seconds=(),
                    max_stories=20,
                    target_size=10,
                    min_size=4,
                    generator_version="w2-05-v1",
                    quiz_pool_enabled=True,
                )

            conn = connect_db(db_path)
            ensure_schema(conn)
            self.assertEqual(count_quizzes_for_story(conn, story_id="story_ok"), 1)

            # Change story input -> new signature/version.
            conn.execute("UPDATE stories SET summary = ? WHERE story_id = ?", ("Summary one changed", "story_ok"))
            conn.commit()
            conn.close()

            with patch("collector.quiz_pool_generator.generate_questions_for_story", side_effect=_mock_generate):
                run_once(
                    db_path=db_path,
                    log_dir=log_dir,
                    ollama_base_url="http://localhost:11434",
                    model="qwen2.5:3b",
                    timeout_seconds=1,
                    max_retries=0,
                    backoff_seconds=(),
                    max_stories=20,
                    target_size=10,
                    min_size=4,
                    generator_version="w2-05-v1",
                    quiz_pool_enabled=True,
                )

            conn = connect_db(db_path)
            ensure_schema(conn)
            self.assertEqual(count_quizzes_for_story(conn, story_id="story_ok"), 2)
            latest = fetch_latest_quiz_metadata(conn, story_id="story_ok")
            self.assertEqual(latest["version"], 2)
            conn.close()


if __name__ == "__main__":
    unittest.main()
