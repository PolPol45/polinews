# W2-05 Quiz Pool QA Report

Date: 2026-03-14  
Task: `W2-05`  
Status: PASS (`coverage >= 80%`)

## Environment
- DB: `data/polinews_w202_realqa.db`
- Generator: `collector/quiz_pool_generator.py`
- Provider: local Ollama `qwen2.5:3b`
- Log dir: `logs/w205_realqa`

## Commands executed

```bash
python3 collector/quiz_pool_generator.py \
  --run-once \
  --db-path data/polinews_w202_realqa.db \
  --max-stories 200 \
  --log-dir logs/w205_realqa
```

```bash
sqlite3 data/polinews_w202_realqa.db "
SELECT COUNT(*) FROM stories WHERE status='publishable';
SELECT COUNT(*) FROM stories WHERE status='publishable' AND quiz_status='quiz_available';
SELECT ROUND(100.0*SUM(CASE WHEN quiz_status='quiz_available' THEN 1 ELSE 0 END)/COUNT(*),2)
FROM stories WHERE status='publishable';
SELECT quiz_unavailable_reason, COUNT(*)
FROM stories
WHERE status='publishable' AND quiz_status='quiz_not_available'
GROUP BY quiz_unavailable_reason
ORDER BY COUNT(*) DESC;
SELECT COUNT(*) FROM quizzes;
SELECT COUNT(*) FROM quiz_questions;
"
```

## Results
- Publishable stories: `49`
- Stories with valid quiz pool (`quiz_available`): `44`
- Coverage: `89.8%`
- `quiz_not_available` reasons:
  - `quiz_generation_failed`: `5`
- Generated quizzes: `44`
- Persisted quiz questions: `269`

## Run log evidence
`logs/w205_realqa/quiz_pool_runs.log`:

```text
20260314193247,2026-03-14T19:32:47.341072+00:00,2026-03-14T19:51:47.253244+00:00,49,44,44,5,0,89.80,25883,
```

## DoD checks
- Pool generation on publishable stories: PASS
- Pool persistence in `quizzes` + `quiz_questions`: PASS
- Story-level quiz state update (`quiz_status`, reason, version, timestamp): PASS
- Coverage target (`>= 80%`): PASS (`89.8%`)
- Unit/integration tests: PASS (`39/39`)

## Notes
- A template fallback is used when model output is too short/noisy, then revalidated against W2-04 quality gates.
- Failed stories remain explicitly tracked with `quiz_not_available` and `quiz_unavailable_reason`.
