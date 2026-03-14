# GITHUB ISSUE — W1-08
# Copia il titolo e il body qui sotto direttamente su github.com/PolPol45/polinews/issues/new

## TITLE
[W1-08] Implement source quality filter — enforce domain policy at normalization time

## LABELS
P0, week-1, backend, codex

## BODY

## Context
`source_policy_v1.md` is now APPROVED with real decisions:
- Min reputation score for story inclusion: **60**
- Initial blocklist: 8 domains (`buzzfeed.com`, `dailymail.co.uk`, `breitbart.com`,
  `infowars.com`, `naturalnews.com`, `thegatewaypundit.com`, `rt.com`, `sputniknews.com`)
- Unknown domains default to `status=watch`, `reputation_score=50`
- Weekly review owner: Freelance

This task integrates the policy into the normalization pipeline (W1-05) so that
domain filtering happens automatically at ingestion time.

## Scope
**IN:** read `source_policy_v1` rules, apply at normalization step after URL parsing
**OUT:** rejected items logged with reason, watch-flagged items marked in DB
**NOT IN SCOPE:** manual review UI, score auto-calculation (manual scoring only in MVP)

## Implementation

### 1. Create `collector/source_policy.py`

```python
# source_policy.py
# Loads domain rules and evaluates a source domain against policy.
# NO external libraries. Uses stdlib only.

BLOCKLIST = {
    "buzzfeed.com",
    "dailymail.co.uk",
    "breitbart.com",
    "infowars.com",
    "naturalnews.com",
    "thegatewaypundit.com",
    "rt.com",
    "sputniknews.com",
}

MIN_REPUTATION_SCORE = 60

# In MVP: policy table is a hardcoded dict + DB table (sources_policy).
# Hardcoded dict is the fallback when domain is not in DB.
DEFAULT_UNKNOWN = {"status": "watch", "reputation_score": 50}

def get_domain_policy(domain: str, db_conn) -> dict:
    """
    Look up domain in sources_policy table.
    Falls back to DEFAULT_UNKNOWN if not found.
    Blocklist always overrides DB.
    """
    ...

def evaluate_source(domain: str, policy: dict) -> tuple[bool, str]:
    """
    Returns (accepted: bool, reason: str).
    reason is empty string if accepted.
    """
    ...
```

### 2. Add `sources_policy` table to DB

```sql
CREATE TABLE IF NOT EXISTS sources_policy (
  domain              TEXT PRIMARY KEY,
  status              TEXT NOT NULL DEFAULT 'watch',  -- allow | watch | deny
  reputation_score    INTEGER NOT NULL DEFAULT 50,
  last_reviewed_at    DATE,
  notes               TEXT,
  created_at          TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed initial blocklist
INSERT INTO sources_policy (domain, status, reputation_score, notes, created_at)
VALUES
  ('buzzfeed.com',          'deny', 10, 'Clickbait-first, unreliable sourcing', NOW()),
  ('dailymail.co.uk',       'deny', 10, 'Chronic accuracy issues', NOW()),
  ('breitbart.com',         'deny',  5, 'Systematic misinformation', NOW()),
  ('infowars.com',          'deny',  0, 'Conspiracy content', NOW()),
  ('naturalnews.com',       'deny',  0, 'Health misinformation', NOW()),
  ('thegatewaypundit.com',  'deny',  5, 'Repeated misinformation', NOW()),
  ('rt.com',                'deny',  5, 'State-controlled propaganda', NOW()),
  ('sputniknews.com',       'deny',  5, 'State-controlled propaganda', NOW())
ON CONFLICT (domain) DO NOTHING;
```

### 3. Integrate into normalizer (W1-05)

After extracting `source_url` from raw item, before writing to `stories`:

```python
from urllib.parse import urlparse
from collector.source_policy import evaluate_source, get_domain_policy

domain = urlparse(source_url).netloc.replace("www.", "")
policy = get_domain_policy(domain, db_conn)
accepted, reason = evaluate_source(domain, policy)

if not accepted:
    log(f"REJECT feed_id={feed_id} raw_id={raw_id} reason=source_policy:{reason}")
    continue

# If watch-flagged, mark in story record
source_watch_flag = (policy["status"] == "watch")
```

### 4. Add `source_watch_flag` column to `stories`

```sql
ALTER TABLE stories ADD COLUMN IF NOT EXISTS source_watch_flag BOOLEAN DEFAULT FALSE;
```

## Acceptance criteria
- [ ] `sources_policy` table created and seeded with 8 blocklist domains
- [ ] Items from blocked domains are rejected at normalization — never reach `stories` table
- [ ] Items from unknown domains are accepted with `source_watch_flag = true`
- [ ] Items from domains with `reputation_score < 60` are rejected with reason `low_reputation`
- [ ] Rejection logged: `REJECT feed_id=<> raw_id=<> reason=source_policy:<reason>`
- [ ] Unit tests cover: blocked domain, unknown domain, low-score domain, allowed domain
- [ ] No external libraries — stdlib + psycopg2 (already in use) only

## Files to create/modify
- `collector/source_policy.py` — NEW: policy lookup and evaluation logic
- `collector/normalizer.py` — MODIFY: integrate source policy check
- `collector/tests/test_source_policy.py` — NEW: unit tests
- `specs/data_model_mvp.sql` — MODIFY: add `sources_policy` table + `source_watch_flag`

## Dependencies
- W1-05 IN PROGRESS (normalizer) — integrate source_policy.py into normalizer
- `docs/mvp_offchain/specs/source_policy_v1.md` — APPROVED ✓ (policy decisions locked)

## Reference
- Policy spec: `docs/mvp_offchain/specs/source_policy_v1.md`
- Schema: `specs/data_model_mvp.sql`
- Min reputation score: 60
- Unknown domain default: watch / score 50
