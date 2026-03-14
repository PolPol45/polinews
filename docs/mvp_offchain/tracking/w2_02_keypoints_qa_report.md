# W2-02 Key Points QA Report

Date: 2026-03-14
Task: `W2-02` (local key-points generation with `Ollama qwen2.5:3b`)

## Runtime Preconditions
- `ollama` binary: not available in environment (`which ollama` -> not found)
- Local endpoint: unreachable (`http://localhost:11434/api/tags`)

## Validation Run
Command executed:

```bash
python3 collector/keypoints_generator.py \
  --run-once \
  --db-path data/polinews_w202_validation_fast.db \
  --max-stories 50 \
  --timeout-seconds 1 \
  --max-retries 0 \
  --backoff-seconds '' \
  --log-dir logs/w202_validation_fast
```

Run summary from logs:
- `processed=50`
- `generated=0`
- `publishable_count=0`
- `not_publishable_count=50`
- main reject reason: `keypoints_generation_failed`

## KPI Check (W2-02 DoD)
- Coverage target: `>= 80%` stories with valid 3-5 key points
- Observed on sample `n=50`: `0%`
- Result: `FAIL` (blocked by missing local Ollama runtime/model)

## Code/Test Status
- Unit tests: `python3 -m unittest discover -s tests -p 'test_*.py'` -> `OK` (29 tests)
- Implemented modules:
  - `collector/keypoints_generator.py`
  - DB/runtime schema extension for `story_key_points` and story publishability fields
  - docs/spec updates for local provider policy

## Decision
`W2-02` cannot be closed as `DONE` until local provisioning is completed:
1. install/start Ollama,
2. pull model `qwen2.5:3b`,
3. rerun QA sample (`>=50`) and confirm coverage target.
