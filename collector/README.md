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
  --dedup-window-hours 24
```

Default output artifacts:
- SQLite DB writes:
  - `stories`
  - `story_sources`
- Run logs: `logs/normalization_runs.log`
- Reject logs: `logs/normalization_rejects.log`
