"""
End-to-end integration test for Poli-News.
Simulates the entire workflow: Ingestion, Enrichment, Auth, Reading Session, Quiz, Rewards, and Analytics.
"""
from __future__ import annotations

import os
import sqlite3
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

# MUST SET ENV VAR BEFORE IMPORTING APP/CONFIG
os.environ["POLINEWS_DB_PATH"] = "data/test_e2e.db"

from polinews.api.app import app
from polinews.config import DB_PATH, PUBLISHER_API_KEY
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema
from polinews.worker.analytics_job import run_analytics_once

class TestEndToEndFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        # Use a test database
        cls.test_db = Path("data/test_e2e.db")
        if cls.test_db.exists():
            cls.test_db.unlink()
        cls.test_db.parent.mkdir(parents=True, exist_ok=True)
        
        cls.conn = connect_db(cls.test_db)
        ensure_schema(cls.conn)
        
        # Insert a mock story to skip actual RSS collection for the test
        cls.story_id = "test_story_123"
        cls.conn.execute("""
            INSERT INTO stories (story_id, topic_slug, headline, summary, published_at, created_at, status, quiz_status)
            VALUES (?, 'politics', 'Test Headline', 'This is a test summary for the E2E flow.', ?, ?, 'publishable', 'quiz_available')
        """, (cls.story_id, cls._now(), cls._now()))
        
        # Insert keypoints and sources
        cls.conn.execute("INSERT INTO story_key_points (key_point_id, story_id, position, text, created_at) VALUES (?, ?, ?, ?, ?)",
                        ("kp1", cls.story_id, 0, "Key point one", cls._now()))
        cls.conn.execute("INSERT INTO story_key_points (key_point_id, story_id, position, text, created_at) VALUES (?, ?, ?, ?, ?)",
                        ("kp2", cls.story_id, 1, "Key point two", cls._now()))
        cls.conn.execute("INSERT INTO story_key_points (key_point_id, story_id, position, text, created_at) VALUES (?, ?, ?, ?, ?)",
                        ("kp3", cls.story_id, 2, "Key point three", cls._now()))
        
        cls.conn.execute("INSERT INTO story_sources (story_source_id, story_id, source_name, source_url, publisher_domain) VALUES (?, ?, ?, ?, ?)",
                        ("ss1", cls.story_id, "Test Source", "https://example.com/test", "example.com"))
        
        # Insert a quiz
        cls.quiz_id = "quiz_123"
        cls.conn.execute("INSERT INTO quizzes (quiz_id, story_id, version, question_pool_size, created_at) VALUES (?, ?, ?, ?, ?)",
                        (cls.quiz_id, cls.story_id, 1, 2, cls._now()))
        
        cls.conn.execute("""
            INSERT INTO quiz_questions (question_id, quiz_id, question_text, task_type, options_json, correct_option_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("q1", cls.quiz_id, "Is this a test?", "comprehension", '[{"option_id": "a", "text": "Yes"}, {"option_id": "b", "text": "No"}]', "a", cls._now()))
        
        cls.conn.execute("""
            INSERT INTO quiz_questions (question_id, quiz_id, question_text, task_type, options_json, correct_option_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, ("q2", cls.quiz_id, "What color is the test?", "detail", '[{"option_id": "a", "text": "Red"}, {"option_id": "b", "text": "Blue"}]', "b", cls._now()))
        
        cls.conn.commit()
        cls.client = TestClient(app)

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat()

    def test_01_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_02_auth_flow(self):
        # 1. Request magic link
        resp = self.client.post("/auth/request-magic-link", json={"email": "test@example.com"})
        self.assertEqual(resp.status_code, 202)
        
        # 2. Extract token from DB (since delivery=log)
        token_row = self.conn.execute("SELECT token FROM magic_link_tokens WHERE email = ?", ("test@example.com",)).fetchone()
        self.assertIsNotNone(token_row)
        token = token_row[0]
        
        # 3. Verify token to get JWT
        resp = self.client.post("/auth/verify", json={"token": token})
        self.assertEqual(resp.status_code, 200)
        self.token = resp.json()["access_token"]
        self.user_id = resp.json()["user_id"]
        
        # 4. Check /me
        resp = self.client.get("/auth/me", headers={"Authorization": f"Bearer {self.token}"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["email"], "test@example.com")

    def test_03_reading_and_quiz_flow(self):
        # 1. Auth with a unique email for this flow to avoid cooldown from previous runs
        email = f"user_{int(time.time())}@example.com"
        resp = self.client.post("/auth/request-magic-link", json={"email": email})
        token = self.conn.execute("SELECT token FROM magic_link_tokens WHERE email = ?", (email,)).fetchone()[0]
        resp = self.client.post("/auth/verify", json={"token": token})
        token_jwt = resp.json()["access_token"]
        
        # 2. Start Session
        resp = self.client.post("/sessions", json={"story_id": self.story_id, "device_type": "desktop"}, headers={"Authorization": f"Bearer {token_jwt}"})
        self.assertEqual(resp.status_code, 200)
        session_id = resp.json()["session_id"]
        
        # 2. Update Session (Engagement)
        resp = self.client.patch(f"/sessions/{session_id}", json={"active_seconds": 45, "scroll_depth": 80})
        self.assertEqual(resp.status_code, 200)
        
        # 4. Get Quiz
        resp = self.client.get(f"/quiz?story_id={self.story_id}", headers={"Authorization": f"Bearer {token_jwt}"})
        self.assertEqual(resp.status_code, 200)
        quiz_data = resp.json()
        self.assertEqual(quiz_data["quiz_id"], self.quiz_id)
        
        # 5. Submit Attempt (Passed)
        answers = [
            {"question_id": q["question_id"], "chosen_option_id": "a" if q["question_id"] == "q1" else "b"}
            for q in quiz_data["questions"]
        ]
        resp = self.client.post("/attempt", json={
            "quiz_id": self.quiz_id,
            "story_id": self.story_id,
            "answers": answers,
            "client_elapsed_seconds": 15
        }, headers={"Authorization": f"Bearer {token_jwt}"})
        
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["passed"])
        self.assertGreater(resp.json()["credits_awarded"], 0)
        
        # 6. Check Balance
        resp = self.client.get("/balance", headers={"Authorization": f"Bearer {token_jwt}"})
        self.assertEqual(resp.status_code, 200)
        self.assertGreater(resp.json()["current_balance"], 0)
        
        return token_jwt # Return for use in test_04 if needed

    def test_04_analytics_aggregation(self):
        # Already populated by test_03 (sequential execution)
        
        # Run Jobs
        run_analytics_once()
        
        # Check Dashboard
        resp = self.client.get("/publisher-dashboard", headers={"X-Publisher-Key": PUBLISHER_API_KEY})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["funnel"]["quiz_passed_total"], 0)
        
        # Check Story Analytics
        resp = self.client.get(f"/analytics/story/{self.story_id}", headers={"X-Publisher-Key": PUBLISHER_API_KEY})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["story_id"], self.story_id)
        self.assertGreater(resp.json()["engagement_score"], 0)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.conn.close()
        # if cls.test_db.exists():
        #     cls.test_db.unlink()

if __name__ == "__main__":
    unittest.main()
