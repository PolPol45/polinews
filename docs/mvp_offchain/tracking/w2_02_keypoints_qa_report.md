# W2-02 Key Points QA Report

Date: 2026-03-14
Task: `W2-02` (local key-points generation with `Ollama qwen2.5:3b`)

## Provisioning Status
- `ollama` installed via Homebrew (`ollama version 0.18.0`).
- Local service active (`brew services start ollama`).
- Model pulled: `qwen2.5:3b` (`ollama list` confirms availability).

## QA Run (sample >= 50)
Validation DB:
- `data/polinews_w202_realqa.db` (copy of `data/polinews.db`)

Command executed:

```bash
python3 collector/keypoints_generator.py \
  --run-once \
  --db-path data/polinews_w202_realqa.db \
  --max-stories 50 \
  --log-dir logs/w202_realqa
```

Run log evidence (`logs/w202_realqa/keypoints_runs.log`):
- `processed=50`
- `generated=49`
- `publishable_count=49`
- `not_publishable_count=1`
- `avg_latency_ms=6172`

Reject evidence (`logs/w202_realqa/keypoints_rejects.log`):
- `1` reject with reason `keypoints_invalid_json`

## KPI Check (W2-02 DoD)
- Coverage formula: `generated / processed`
- Coverage observed: `49 / 50 = 98%`
- Target: `>= 80%`
- Result: `PASS`

## SQL Cross-Check (same validation DB)
- `stories_total = 3407`
- `publishable = 49`
- `not_publishable = 3358`
- `story_key_points rows = 152`
- `avg key points per publishable story ≈ 3.10`

## Decision
W2-02 QA target met after local provisioning.
Task can be marked `DONE`.
