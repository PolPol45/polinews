# W1-10 Chaos Note — Stale Fallback Validation

Date: 2026-03-14  
Task: `W1-10`  
Objective: validate stale fallback activation after 3 consecutive feed failures.

## Setup

- Test feed registry (temporary): `/tmp/w1_10_feeds_failure.csv`
- Failing feed used:
  - `feed_id=feed_chaos_failure_us`
  - `url=http://127.0.0.1:9/rss` (intentionally unreachable)
- State file: `/tmp/w1_10_chaos_state.json`
- Logs dir: `/tmp/w1_10_chaos_logs`
- DB: `/tmp/w1_10_chaos.db`

Command executed (3 consecutive runs):

```bash
python3 collector/rss_collector.py \
  --run-once \
  --feeds-csv /tmp/w1_10_feeds_failure.csv \
  --db-path /tmp/w1_10_chaos.db \
  --log-dir /tmp/w1_10_chaos_logs \
  --state-path /tmp/w1_10_chaos_state.json
```

## Results

Run log lines:

1. `...,0,0,1,fetch_error`
2. `...,0,0,1,fetch_error`
3. `...,0,0,1,fetch_error;stale_threshold_reached`

Reject log lines:

- 3 entries with reason code `fetch_error` (one per run).

State file after run 3:

```json
{
  "feed_chaos_failure_us": 3
}
```

## Conclusion

- Stale fallback threshold is correctly enforced at 3 consecutive failures.
- On threshold crossing, run log correctly appends `stale_threshold_reached`.
- W1-10 DoD met: feed can fail without blocking runtime flow, with explicit stale-mode alert signal in logs.
