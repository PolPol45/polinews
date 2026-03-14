# W1-06 Canonical URL QA Report

Date: 2026-03-14  
Task: `W1-06`  
Scope: Canonical URL resolver + normalizer integration + dedup compatibility

## 1) Runtime integration evidence

Validation DB: `data/polinews_w106_validation.db`  
Command used:

```bash
python3 collector/normalizer.py \
  --run-once \
  --db-path data/polinews_w106_validation.db \
  --log-dir logs/w106_validation \
  --canonical-timeout-seconds 2 \
  --canonical-max-retries 0 \
  --canonical-backoff-seconds ''
```

First run summary (`logs/w106_validation/normalization_runs.log`):

`733cb3e79a69,...,processed=3040,accepted=2768,rejected=272,duplicates=272,canonical_resolved=0,canonical_fallback=3040,canonical_error=0`

Second run summary (idempotence check):

`a40e10546900,...,processed=3040,accepted=0,rejected=3040,duplicates=3040,canonical_resolved=0,canonical_fallback=3040,canonical_error=0`

DB checks after rerun:

- `feed_items_raw = 3040`
- `stories = 2768`
- `story_sources = 2768`
- `dedup_registry = 2768`
- `story_sources.canonical_url` null/empty rows = `0`

Result:

- Dedup remains idempotent after W1-06 integration.
- Canonical URL is persisted for all inserted `story_sources`.

## 2) Mandatory QA sample (100 real records)

Sample source: first 100 rows from `data/polinews.db.feed_items_raw` ordered by `fetched_at, raw_id`.

Mode counts:

- `resolved_direct = 0`
- `resolved_redirect = 0`
- `fallback_source = 100`
- `error = 0`

Metric:

- `canonical_usable_rate = (resolved_direct + resolved_redirect + fallback_source) / processed`
- `canonical_usable_rate = (0 + 0 + 100) / 100 = 1.00 (100%)`

DoD check:

- Target `>= 90%` met.
- Per decision lock, fallback counts as resolved for MVP usability.

## 3) 10 sample records (resolved via fallback)

| raw_id | feed_id | mode | raw_link_host | source_url | canonical_url |
|---|---|---|---|---|---|
| `0004b388-7a09-4789-aae6-f81603fdd6de` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://thedispatch.com` | `https://thedispatch.com` |
| `008c7691-9ec3-4106-b0ea-779419f6f59c` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://www.espn.com` | `https://www.espn.com` |
| `126de6f7-19e8-4fbb-b75a-356bf0f6817e` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://georgiarecorder.com` | `https://georgiarecorder.com` |
| `1534c6f9-98c5-44a5-b90b-9441d5682e4e` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://spectrumlocalnews.com` | `https://spectrumlocalnews.com` |
| `1718525d-8120-43ca-85c8-2f0de0927439` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://www.coloradopolitics.com` | `https://www.coloradopolitics.com` |
| `1a1d9f37-9ab0-41b1-8d38-ca4de8179ef9` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://wisconsinindependent.com` | `https://wisconsinindependent.com` |
| `1d661709-3357-4fa9-9665-b3d863fef8b9` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://theweek.com` | `https://theweek.com` |
| `1fa82dfb-b257-4f2f-961e-92e481efdcfe` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://kentuckylantern.com` | `https://kentuckylantern.com` |
| `218ee0a9-0f9f-4cd3-97be-66184587c5dc` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://www.ktvu.com` | `https://www.ktvu.com` |
| `2436dea9-8028-47e5-82f4-b4d3f99e19af` | `feed_politics_us` | `fallback_source` | `news.google.com` | `https://www.euractiv.com` | `https://www.euractiv.com` |

## 4) Notes

- Dataset reality at this stage: all `payload_json.link` are Google News article URLs (`news.google.com/...`), so direct canonical resolution is not observed in this sample.
- The resolver still attempts canonical redirect resolution first; when not available, it falls back to normalized `source_url` and keeps pipeline usable.
