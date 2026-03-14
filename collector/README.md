# RSS Collector (W1-04)

Run once on all active feeds:

```bash
python3 collector/rss_collector.py --run-once --db-path data/polinews.db
```

Optional overrides:

```bash
python3 collector/rss_collector.py \
  --run-once \
  --feeds-csv docs/mvp_offchain/specs/feed_registry_v1.csv \
  --db-path data/polinews.db \
  --log-dir logs \
  --state-path data/stale_state.json
```

Default output artifacts:
- SQLite DB: `data/polinews.db`
- Run logs: `logs/ingestion_runs.log`
- Reject logs: `logs/ingestion_rejects.log`
- Stale counters: `data/stale_state.json`

Exit codes:
- `0`: run completed
- `1`: global runtime error (for example missing CSV/DB access issues)

---

# Feed Normalizer (W1-05)

Run once on all rows in `feed_items_raw`:

```bash
python3 collector/normalizer.py --run-once --db-path data/polinews.db
```

Optional overrides:

```bash
python3 collector/normalizer.py \
  --run-once \
  --db-path data/polinews.db \
  --feeds-csv docs/mvp_offchain/specs/feed_registry_v1.csv \
  --topics-file docs/mvp_offchain/specs/topics_v1.md \
  --log-dir logs \
  --dedup-window-hours 24 \
  --canonical-timeout-seconds 8 \
  --canonical-max-retries 3 \
  --canonical-backoff-seconds 1,3,9
```

Default output artifacts:
- SQLite DB writes:
  - `stories`
  - `story_sources`
- Run logs: `logs/normalization_runs.log`
- Reject logs: `logs/normalization_rejects.log`
- Canonical URL modes: `resolved_direct`, `resolved_redirect`, `fallback_source`

---

# Key Points Generator (W2-02)

Local prerequisites (free stack):

```bash
ollama --version
ollama pull qwen2.5:3b
curl -sS http://localhost:11434/api/tags
```

Run once on non-publishable stories:

```bash
python3 collector/keypoints_generator.py --run-once --db-path data/polinews.db
```

Optional overrides:

```bash
python3 collector/keypoints_generator.py \
  --run-once \
  --db-path data/polinews.db \
  --log-dir logs \
  --ollama-base-url http://localhost:11434 \
  --model qwen2.5:3b \
  --timeout-seconds 25 \
  --max-retries 2 \
  --backoff-seconds 1,3 \
  --max-stories 150
```

Default output artifacts:
- SQLite DB writes:
  - `story_key_points`
  - `stories.status`, `stories.publishability_reason`, `stories.keypoints_generated_at`
- Run logs: `logs/keypoints_runs.log`
- Reject logs: `logs/keypoints_rejects.log`
