"""
Quiz engine router — GET /quiz and POST /attempt.

GET /quiz   → serves a randomized question set (never exposes correct_option_id)
POST /attempt → evaluates answers, enforces fraud rules, issues credits
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import date, datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from polinews.api.auth import get_current_user
from polinews.config import DB_PATH
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

router = APIRouter(tags=["quiz"])

# ── Constants ─────────────────────────────────────────────────────────────────
PASS_THRESHOLD = 0.70
MAX_ATTEMPTS_PER_DAY = 3
COOLDOWN_SECONDS = 120
MIN_ELAPSED_SECONDS = 8       # anti-bot
BASE_REWARD = 10              # credits for quiz_pass
NEW_USER_DAYS = 7             # days a user is considered "new"
NEW_USER_MULTIPLIER = 0.3
DAILY_CAP = 50                # max credits earned per user per day


# ── Pydantic models ───────────────────────────────────────────────────────────

class QuizOption(BaseModel):
    option_id: str
    text: str


class QuizQuestion(BaseModel):
    question_id: str
    text: str
    options: list[QuizOption]


class QuizResponse(BaseModel):
    quiz_id: str
    story_id: str
    questions: list[QuizQuestion]
    attempts_remaining: int
    cooldown_seconds: int


class AnswerItem(BaseModel):
    question_id: str
    chosen_option_id: str


class AttemptRequest(BaseModel):
    quiz_id: str
    story_id: str
    answers: list[AnswerItem]
    client_elapsed_seconds: int = 0


class AttemptResponse(BaseModel):
    passed: bool
    score_raw: float
    score_percent: int
    credits_awarded: int
    balance_preview: int
    cooldown_seconds: int
    attempts_remaining: int
    feedback: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _today_utc() -> str:
    return date.today().isoformat()


def _conn() -> sqlite3.Connection:
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    return conn


def _count_attempts_today(conn: sqlite3.Connection, user_id: str, story_id: str) -> int:
    today = _today_utc()
    row = conn.execute(
        """
        SELECT COUNT(*) FROM attempts
        WHERE user_id = ? AND story_id = ?
          AND DATE(created_at) = ?
        """,
        (user_id, story_id, today),
    ).fetchone()
    return int(row[0]) if row else 0


def _seconds_since_last_attempt(conn: sqlite3.Connection, user_id: str, story_id: str) -> float:
    row = conn.execute(
        """
        SELECT created_at FROM attempts
        WHERE user_id = ? AND story_id = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (user_id, story_id),
    ).fetchone()
    if row is None:
        return float("inf")
    try:
        last = datetime.fromisoformat(str(row[0]))
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - last).total_seconds()
    except ValueError:
        return float("inf")


def _get_latest_quiz(conn: sqlite3.Connection, story_id: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT quiz_id, version
        FROM quizzes
        WHERE story_id = ?
        ORDER BY version DESC
        LIMIT 1
        """,
        (story_id,),
    ).fetchone()


def _get_quiz_questions(conn: sqlite3.Connection, quiz_id: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT question_id, question_text, task_type, options_json, correct_option_id
        FROM quiz_questions
        WHERE quiz_id = ?
        ORDER BY question_id ASC
        """,
        (quiz_id,),
    ).fetchall()
    questions = []
    for r in rows:
        try:
            options = json.loads(str(r["options_json"] or "[]"))
        except json.JSONDecodeError:
            options = []
        questions.append({
            "question_id": str(r["question_id"]),
            "question_text": str(r["question_text"]),
            "task_type": str(r["task_type"]),
            "options": options,
            "correct_option_id": str(r["correct_option_id"]),
        })
    return questions


def _select_question_set(questions: list[dict[str, Any]], *, target: int = 3) -> list[dict[str, Any]]:
    """Pick 2–3 questions ensuring at least 1 comprehension + 1 detail."""
    import random
    comprehension = [q for q in questions if q["task_type"] == "comprehension"]
    detail = [q for q in questions if q["task_type"] == "detail"]

    selected: list[dict[str, Any]] = []
    if comprehension:
        selected.append(random.choice(comprehension))
    if detail:
        selected.append(random.choice(detail))

    # Fill remaining slots from the rest (avoiding duplicates)
    selected_ids = {q["question_id"] for q in selected}
    remaining = [q for q in questions if q["question_id"] not in selected_ids]
    random.shuffle(remaining)
    for q in remaining:
        if len(selected) >= target:
            break
        selected.append(q)
        selected_ids.add(q["question_id"])

    return selected[:target]


def _get_user_balance(conn: sqlite3.Connection, user_id: str) -> int:
    row = conn.execute(
        "SELECT COALESCE(SUM(delta_credits), 0) FROM rewards_ledger WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row[0]) if row else 0


def _get_credits_earned_today(conn: sqlite3.Connection, user_id: str) -> int:
    today = _today_utc()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(delta_credits), 0) FROM rewards_ledger
        WHERE user_id = ? AND delta_credits > 0 AND DATE(created_at) = ?
        """,
        (user_id, today),
    ).fetchone()
    return int(row[0]) if row else 0


def _already_rewarded(conn: sqlite3.Connection, user_id: str, story_id: str) -> bool:
    row = conn.execute(
        """
        SELECT 1 FROM rewards_ledger
        WHERE user_id = ? AND story_id = ? AND reason = 'quiz_pass'
        LIMIT 1
        """,
        (user_id, story_id),
    ).fetchone()
    return row is not None


def _is_new_user(conn: sqlite3.Connection, user_id: str) -> bool:
    from datetime import timedelta
    row = conn.execute("SELECT created_at FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not row:
        return False
    try:
        created = datetime.fromisoformat(str(row["created_at"]))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - created).days < NEW_USER_DAYS
    except ValueError:
        return False


def _emit_fraud_signal(
    conn: sqlite3.Connection,
    *,
    user_id: str,
    signal_type: str,
    severity: str = "low",
    details: dict[str, Any] | None = None,
    attempt_id: str | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO fraud_signals (signal_id, user_id, signal_type, severity, details_json, attempt_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            user_id,
            signal_type,
            severity,
            json.dumps(details or {}),
            attempt_id,
            _utc_now(),
        ),
    )


# ── GET /quiz ─────────────────────────────────────────────────────────────────

@router.get("/quiz", response_model=QuizResponse)
def get_quiz(
    story_id: str = Query(..., description="Story ID to get quiz for"),
    current_user: Annotated[dict[str, str], Depends(get_current_user)] = ...,  # type: ignore[assignment]
) -> QuizResponse:
    """
    Returns a randomized quiz for a story.
    - 404 if story or quiz not found
    - 409 if quiz not available
    - 429 if attempt limit or cooldown reached
    """
    user_id = current_user["user_id"]
    conn = _conn()
    try:
        # Check story exists and is publishable
        story_row = conn.execute(
            "SELECT story_id, status, quiz_status FROM stories WHERE story_id = ? LIMIT 1",
            (story_id,),
        ).fetchone()
        if story_row is None:
            raise HTTPException(status_code=404, detail="story_not_found")
        if story_row["status"] != "publishable":
            raise HTTPException(status_code=409, detail="story_not_publishable")
        if str(story_row["quiz_status"] or "") != "quiz_available":
            raise HTTPException(status_code=409, detail="quiz_not_available")

        # Attempt rate limits
        attempts_today = _count_attempts_today(conn, user_id, story_id)
        remaining = MAX_ATTEMPTS_PER_DAY - attempts_today
        if remaining <= 0:
            raise HTTPException(status_code=429, detail="attempts_exhausted", headers={"Retry-After": "86400"})

        elapsed_since_last = _seconds_since_last_attempt(conn, user_id, story_id)
        if elapsed_since_last >= COOLDOWN_SECONDS:
            cooldown_left = 0
        else:
            cooldown_left = int(COOLDOWN_SECONDS - elapsed_since_last)
            
        if cooldown_left > 0:
            raise HTTPException(
                status_code=429,
                detail=f"cooldown_active",
                headers={"Retry-After": str(cooldown_left)},
            )

        # Load and select questions
        quiz_row = _get_latest_quiz(conn, story_id)
        if quiz_row is None:
            raise HTTPException(status_code=404, detail="quiz_not_found")
        quiz_id = str(quiz_row["quiz_id"])

        all_questions = _get_quiz_questions(conn, quiz_id)
        if len(all_questions) < 2:
            raise HTTPException(status_code=409, detail="quiz_not_available")

        selected = _select_question_set(all_questions, target=3)

    finally:
        conn.close()

    # Build response — NEVER include correct_option_id
    quiz_questions = [
        QuizQuestion(
            question_id=q["question_id"],
            text=q["question_text"],
            options=[QuizOption(**opt) for opt in q["options"]],
        )
        for q in selected
    ]

    return QuizResponse(
        quiz_id=quiz_id,
        story_id=story_id,
        questions=quiz_questions,
        attempts_remaining=remaining,
        cooldown_seconds=0,
    )


# ── POST /attempt ─────────────────────────────────────────────────────────────

@router.post("/attempt", response_model=AttemptResponse)
def submit_attempt(
    body: AttemptRequest,
    current_user: Annotated[dict[str, str], Depends(get_current_user)] = ...,  # type: ignore[assignment]
) -> AttemptResponse:
    """
    Evaluate quiz answers and award credits if passed.
    Enforces: cooldown, daily cap, bot detection, one-reward-per-story.
    """
    user_id = current_user["user_id"]
    conn = _conn()
    attempt_id = str(uuid.uuid4())
    try:
        # Anti-bot: minimum elapsed time
        if body.client_elapsed_seconds < MIN_ELAPSED_SECONDS:
            _emit_fraud_signal(
                conn, user_id=user_id,
                signal_type="too_fast_attempt",
                severity="medium",
                details={"elapsed": body.client_elapsed_seconds, "story_id": body.story_id},
            )
            conn.commit()
            raise HTTPException(status_code=400, detail="attempt_too_fast")

        # Rate limits
        attempts_today = _count_attempts_today(conn, user_id, body.story_id)
        if attempts_today >= MAX_ATTEMPTS_PER_DAY:
            raise HTTPException(status_code=429, detail="attempts_exhausted")

        elapsed_since = _seconds_since_last_attempt(conn, user_id, body.story_id)
        if elapsed_since >= COOLDOWN_SECONDS:
            cooldown_left = 0
        else:
            cooldown_left = int(COOLDOWN_SECONDS - elapsed_since)
            
        if cooldown_left > 0:
            raise HTTPException(status_code=429, detail="cooldown_active")

        # Validate quiz_id belongs to story
        quiz_row = conn.execute(
            "SELECT quiz_id FROM quizzes WHERE quiz_id = ? AND story_id = ? LIMIT 1",
            (body.quiz_id, body.story_id),
        ).fetchone()
        if quiz_row is None:
            raise HTTPException(status_code=404, detail="quiz_not_found_for_story")

        # Load correct answers
        correct_map: dict[str, str] = {}
        q_rows = conn.execute(
            "SELECT question_id, correct_option_id FROM quiz_questions WHERE quiz_id = ?",
            (body.quiz_id,),
        ).fetchall()
        for r in q_rows:
            correct_map[str(r["question_id"])] = str(r["correct_option_id"])

        # Validate answer question_ids
        submitted_ids = {a.question_id for a in body.answers}
        if not submitted_ids.issubset(correct_map.keys()):
            raise HTTPException(status_code=400, detail="invalid_question_ids")

        # Score
        total = len(body.answers)
        if total == 0:
            raise HTTPException(status_code=400, detail="no_answers_submitted")

        correct_count = sum(
            1 for a in body.answers
            if correct_map.get(a.question_id) == a.chosen_option_id
        )
        score_raw = correct_count / total
        passed = score_raw >= PASS_THRESHOLD
        score_percent = round(score_raw * 100)

        # Record attempt
        conn.execute(
            """
            INSERT INTO attempts (attempt_id, user_id, story_id, quiz_id,
                                  answers_json, score_raw, passed, client_elapsed_seconds, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id, user_id, body.story_id, body.quiz_id,
                json.dumps([a.model_dump() for a in body.answers]),
                score_raw, int(passed), body.client_elapsed_seconds, _utc_now(),
            ),
        )

        # Calculate credits
        credits_awarded = 0
        if passed and not _already_rewarded(conn, user_id, body.story_id):
            raw_reward = BASE_REWARD
            if _is_new_user(conn, user_id):
                raw_reward = int(raw_reward * NEW_USER_MULTIPLIER)

            # Check daily cap
            earned_today = _get_credits_earned_today(conn, user_id)
            credits_awarded = min(raw_reward, max(0, DAILY_CAP - earned_today))

            if credits_awarded > 0:
                conn.execute(
                    """
                    INSERT INTO rewards_ledger
                      (entry_id, user_id, story_id, delta_credits, reason, reference_id, created_at)
                    VALUES (?, ?, ?, ?, 'quiz_pass', ?, ?)
                    """,
                    (str(uuid.uuid4()), user_id, body.story_id,
                     credits_awarded, attempt_id, _utc_now()),
                )

        balance = _get_user_balance(conn, user_id)
        remaining = MAX_ATTEMPTS_PER_DAY - (_count_attempts_today(conn, user_id, body.story_id))
        conn.commit()

    except HTTPException:
        conn.rollback()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    feedback = (
        "Great job! Credits awarded." if passed and credits_awarded > 0
        else "Passed! (already rewarded for this story)" if passed
        else f"Not passed — score {score_percent}%. Try again."
    )

    return AttemptResponse(
        passed=passed,
        score_raw=round(score_raw, 4),
        score_percent=score_percent,
        credits_awarded=credits_awarded,
        balance_preview=balance,
        cooldown_seconds=COOLDOWN_SECONDS if not passed else 0,
        attempts_remaining=max(0, remaining),
        feedback=feedback,
    )
