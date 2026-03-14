# quiz_spec_v1

Version: `2026-03-14-v2`
Owner: Founder
Status: APPROVED - locked for W2 implementation

## 1. Quiz format (locked)
- Attempt format: `2-3` questions per attempt.
- Runtime selection from story-level question pool.
- Required mix in each attempt:
  - `>=1` question with type `comprehension`
  - `>=1` question with type `detail`

## 2. Availability state and reason codes
- Story-level quiz state:
  - `quiz_available`
  - `quiz_not_available`
- Locked reason codes for `quiz_not_available`:
  - `pool_too_small`
  - `pool_quality_failed`
  - `story_not_publishable`
  - `quiz_generation_failed`
  - `quiz_temporarily_disabled`

## 3. Pool requirements
- Target pool size: `10` candidate questions per story when possible.
- Minimum viable pool: `4` questions for short stories.
- If pool is below minimum or fails quality checks, set story quiz state to `quiz_not_available`.

## 4. Contract-level output (GET /quiz)
- Required fields:
  - `quiz_id`
  - `story_id`
  - `questions[]`
  - `attempts_remaining`
  - `cooldown_seconds`
- `questions[]` shape:
  - `question_id`
  - `text`
  - `options[]`
- `options[]` shape:
  - `option_id`
  - `text`

## 5. Attempt rules and scoring
- Max attempts per story per user per day: `3`.
- Cooldown between attempts: `120` seconds.
- One reward per story/account remains enforced by ledger policy.

Scoring rules (locked):
- `score_raw = correct_answers / total_questions`
- `pass = score_raw >= 0.70`
- `score_percent` is display only and uses nearest-integer half-up rounding.

## 6. Error handling alignment
`GET /quiz?story_id=`
- `404`: story or quiz not found
- `409`: quiz state is `quiz_not_available`
- `429`: rate limit or cooldown

`POST /attempt`
- `400`: invalid payload
- `404`: story/quiz not found
- `409`: quiz not available for story
- `429`: rate limit or cooldown

## 7. Consistency with story payload (W2-03)
- `GET /stories/:story_id` field `quiz_available` must be `true` only when runtime quiz is available.
- `comment_enabled` remains independent from quiz availability (W2-08 placeholder).

## 8. Test cases (spec-only)
1. Valid quiz with 2 questions
- Input: story in `quiz_available`, question set size `2` with required type mix.
- Expected: `GET /quiz` returns `200` with all required fields and `questions.length=2`.

2. Valid quiz with 3 questions
- Input: story in `quiz_available`, question set size `3` with required type mix.
- Expected: `GET /quiz` returns `200` with all required fields and `questions.length=3`.

3. Pool insufficient
- Input: story pool below minimum (`<4`).
- Expected: story quiz state `quiz_not_available`, reason `pool_too_small`, `GET /quiz` returns `409`.

4. Attempts exhausted
- Input: user already used 3 attempts for same story/day.
- Expected: `GET /quiz` returns `429` or `POST /attempt` returns `429`, `attempts_remaining=0`.

5. Cooldown active
- Input: attempt submitted less than 120s after previous attempt.
- Expected: `POST /attempt` returns `429` with residual `cooldown_seconds`.
