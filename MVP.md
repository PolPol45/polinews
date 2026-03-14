# Poli-News

**Version:** v0.2 — MVP Off-Chain + Blockchain Revenue Model  
**Date:** 2026-03-14  
**Status:** Week 1 in progress — governance complete, feed registry frozen, ingestion pipeline pending

> *Poli-News is a Proof-of-Reading Incentive Layer that converts verified editorial attention into measurable engagement, sustainable token rewards, and licensable AI training data.*

---

## Table of Contents

1. [What Poli-News Is](#1-what-poli-news-is)
2. [Repository State (as of 2026-03-14)](#2-repository-state-as-of-2026-03-14)
3. [System Architecture](#3-system-architecture)
4. [MVP Off-Chain Layer](#4-mvp-off-chain-layer)
5. [Blockchain Layer (Phase 2)](#5-blockchain-layer-phase-2)
6. [Revenue Streams](#6-revenue-streams)
   - 6.1 [Publisher Subscription (Core)](#61-publisher-subscription-core)
   - 6.2 [AI Training Data Licensing](#62-ai-training-data-licensing)
   - 6.3 [Human Verification Tasks (RLHF Data Sales)](#63-human-verification-tasks-rlhf-data-sales)
   - 6.4 [Verified Attention Analytics](#64-verified-attention-analytics)
7. [Token Economics ($POLI)](#7-token-economics-poli)
8. [Data Model](#8-data-model)
9. [API Reference](#9-api-reference)
10. [Feed Registry](#10-feed-registry)
11. [Anti-Fraud System](#11-anti-fraud-system)
12. [KPI Framework](#12-kpi-framework)
13. [Pilot Plan & Decision Gates](#13-pilot-plan--decision-gates)
14. [Tech Stack & Provider Reference](#14-tech-stack--provider-reference)
15. [Compliance Notes](#15-compliance-notes)

---

## 1. What Poli-News Is

Poli-News is an application layer that sits on top of any digital publisher and turns passive reading into three monetizable outputs:

1. **Verified reads** — users prove they understood an article by passing a short quiz. The publisher pays for this signal because it is qualitatively different from a pageview.
2. **Behavioral datasets** — reading time, comprehension scores, quiz answer pairs, and topic interest signals are structured and licensed as AI training data.
3. **Human annotation tasks** — some quiz questions double as micro-annotation tasks (misinformation detection, summary validation, sentiment labeling) sold to AI labs.

The user is rewarded with `$POLI`, an ERC-20 utility token backed by a protocol treasury funded by publishers and advertisers.

**The core loop:**

```
Publisher pays USDC into treasury
    → Reader reads article
    → Reader passes quiz (20–60 seconds)
    → Backend issues signed voucher
    → Reader claims $POLI on-chain
    → Treasury receives more USDC from data licensing and analytics
    → Token value is supported by real cashflows
```

No wallets required in the MVP. No KYC. No blockchain complexity for the pilot publisher. Phase 2 introduces on-chain claiming once the off-chain loop is validated.

---

## 2. Repository State (as of 2026-03-14)

### Completed

| ID | Task | Evidence |
|----|------|----------|
| G-01 | Board created (Backlog / In Progress / Blocked / Done) | `tracking/KANBAN_BOARD.md` |
| G-03 | SLA defined (Critical <24h, High <48h) | `governance/sla_mvp.md` |
| G-04 | Environment naming (`dev / staging / pilot`) | `governance/env_naming.md` |
| G-05 | Issue templates (Bug / Feature / Fraud / Ops) | `governance/issue_templates.md` |
| W1-01 | Topic taxonomy frozen (10 topics, slug rules validated) | `specs/topics_v1.md` |
| W1-02 | Feed registry built and frozen (30 feeds, US/UK/IT) | `specs/feed_registry_v1.csv` |

### Specs written and ready (tasks not yet formally closed)

| Spec file | Content |
|-----------|---------|
| `specs/ingestion_policy_v1.md` | 15-min refresh, 8s timeout, 3 retries, stale mode |
| `specs/source_policy_v1.md` | allow/watch/deny per domain, min reputation 40 |
| `specs/attribution_policy_v1.md` | mandatory source block above quiz, no full-text copy |
| `specs/story_template_v1.md` | headline / snippet / key-points / sources / quiz box |
| `specs/quiz_spec_v1.md` | 2–3 questions, 70% pass threshold, 3 attempts/day |
| `specs/reward_policy_v1.md` | 10 base / +5 comment / 50 daily cap / 0.3× new-user |
| `specs/kpi_spec_v1.md` | 6 primary KPIs, alert thresholds, 15-min dashboard refresh |
| `specs/data_model_mvp.sql` | Full schema: users, stories, quizzes, attempts, ledger, fraud |
| `specs/api_contract_mvp.md` | All public endpoints with request/response shapes |

### Blocked

| ID | Blocker |
|----|---------|
| G-02 | 28-day calendar not created — depends on founder action |

### Next open tasks (Week 1)

`W1-03` Implement RSS collector → `W1-04` Normalization → `W1-05`…`W1-09` (see `MASTER_CHECKLIST.md`)

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      OFF-CHAIN LAYER (MVP)                  │
│                                                             │
│  Google News RSS ──► Ingestion Worker ──► Normalization     │
│                            │                    │           │
│                       Source Filter         Dedup + URL     │
│                            │                Resolver        │
│                            ▼                    │           │
│                      Stories DB ◄───────────────┘          │
│                            │                               │
│               ┌────────────┼────────────┐                  │
│               ▼            ▼            ▼                  │
│          Quiz Engine   Comment      Attribution             │
│               │        Engine       Guard                   │
│               ▼            │                               │
│          Rewards Ledger ◄──┘                               │
│               │                                            │
│          Fraud Engine                                       │
│               │                                            │
│       Publisher Dashboard                                   │
│                                                             │
├─────────────────── DATA LAYER ──────────────────────────────┤
│                                                             │
│  reading_sessions   quiz_qa_pairs   comprehension_events   │
│  annotation_tasks   topic_signals   attention_analytics     │
│                                                             │
├───────────────── BLOCKCHAIN LAYER (Phase 2) ────────────────┤
│                                                             │
│  RewardDistributor.sol ──► ReadingVault.sol ──► PoliToken  │
│         (Sepolia → Base/Arbitrum + Solana bridge)           │
└─────────────────────────────────────────────────────────────┘
```

### Component responsibilities

| Component | Role | Key dependencies |
|-----------|------|-----------------|
| Ingestion Worker | Fetches and parses Google News RSS every 15 min | `feedparser`, `httpx`, PostgreSQL |
| Normalization | Extracts title/snippet/source/date, validates mandatory fields | Internal rules, no LLM in MVP |
| Quiz Engine | Generates question pool per story, serves randomized 2–3 question sets | OpenAI `gpt-4o-mini` for pool generation, PostgreSQL for storage |
| Comment Engine | Validates comment quality (length, dedup, spam patterns) | Internal heuristics, optional `fasttext` for language check |
| Rewards Ledger | Append-only credit/debit/revoke log per user | PostgreSQL with `entry_id`, `reason`, `delta_credits` |
| Fraud Engine | Velocity checks, clustering, rate limiting | PostgreSQL + Redis for counters |
| Data Layer | Stores behavioral data structured for AI export | PostgreSQL + S3-compatible storage (Cloudflare R2 or AWS S3) |
| Blockchain Layer | Issues $POLI on-chain against off-chain vouchers | Solidity (Foundry), Ethereum Sepolia, Solana Devnet |

---

## 4. MVP Off-Chain Layer

### 4.1 Content ingestion

Feeds are sourced from Google News RSS. The registry covers 30 active feeds across 3 locales (en-US, en-GB, it-IT) and 10 topic slugs.

**Topics (frozen, do not rename during pilot):**

| Slug | Description |
|------|-------------|
| `politics` | Elections, institutions, diplomacy, public policy |
| `economy` | Macro trends, inflation, central banks, labor |
| `world` | International news and geopolitics |
| `technology` | AI, software, hardware, platforms |
| `health` | Public health, medicine, healthcare systems |
| `climate` | Energy transition, climate risks, environment |
| `markets` | Equity, bonds, FX, commodities |
| `security` | Cybersecurity, defense, intelligence |
| `business` | Company news, strategy, M&A |
| `science` | Research, discoveries, science policy |

**Ingestion policy (summary):** 15-minute refresh with ±60s jitter. 8s request timeout. Max 3 retries with backoff (1s / 3s / 9s). Stale mode activates after 3 consecutive failures — system continues serving last successful snapshot and raises an alert. User-agent: `PoliNewsMVPFeedCollector/1.0`.

### 4.2 Story format

Each story page renders: topic badge → headline → snippet (≤320 chars) → key points (3–5 bullets synthesized internally) → source list (name + outbound link, must appear above quiz box) → verification box → credits balance teaser.

Content guardrails: no full-text copy of source articles, no paywalled content reproduction, every page shows the disclaimer *"Summary generated by Poli-News from public source metadata"*.

### 4.3 Quiz system

- Pool size target: 10 candidate questions per story. Minimum viable: 4 (for short stories).
- At runtime: 2–3 questions served, randomized from pool. Mix: at least 1 comprehension + at least 1 detail question.
- Pass threshold: 70%.
- Attempt limits: max 3 per story per day, 120s cooldown between attempts.
- One reward per story per account — enforced at ledger write time.

**Quiz pool generation (provider: OpenAI):**

```python
# Provider: OpenAI — model: gpt-4o-mini (cost-efficient for bulk generation)
# Estimated cost: ~$0.001 per story pool (10 questions)
# API docs: https://platform.openai.com/docs/api-reference/chat

response = openai.chat.completions.create(
    model="gpt-4o-mini",
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": QUIZ_GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": f"Story: {story_headline}\n\n{story_snippet}\n\nKey points:\n{key_points}"}
    ]
)
```

The system prompt instructs the model to output a JSON array of question objects: `{question_id, question_text, options: [{id, text}], correct_option_id, type: "comprehension"|"detail", difficulty: 1–3}`.

Anti-abuse checks: reject attempts where `client_elapsed_seconds` < 8 (configurable). Flag repeated identical answer patterns across accounts via `fraud_signals`.

### 4.4 Reward policy

| Rule | Value |
|------|-------|
| `base_reward` | 10 credits for quiz pass |
| `bonus_reward` | +5 credits for valid comment |
| `daily_cap` | 50 credits per user per day |
| `new_user_multiplier` | 0.3× for first 7 days |
| Revocation | Allowed for: `fraud`, `duplicate_reward`, `policy_violation` |

Revocation writes a negative ledger entry with reason code — prior entries are never deleted, preserving the audit trail.

### 4.5 Widget integration

One JS snippet. No server-side changes required on the publisher side.

```html
<script src="https://cdn.polinews.io/widget.js"
  data-publisher-id="pub_001"
  data-article-id="art_2026_03_001"
  data-placement="scroll_threshold"
  data-scroll-threshold="70">
</script>
```

Tracked events: `box_viewed`, `quiz_started`, `quiz_passed`, `comment_submitted`, `reward_credited`, `reward_redeemed`.

### 4.6 Authentication (MVP)

Magic link email (no password). Optionally: Google/GitHub OAuth. Session stored as a signed JWT with 7-day expiry. Provider options:

- **Self-hosted:** [Lucia Auth](https://lucia-auth.com/) + PostgreSQL sessions
- **Managed (recommended for MVP speed):** [Clerk](https://clerk.com/) — free tier covers pilot scale, magic link built-in, ~10 min integration

---

## 5. Blockchain Layer (Phase 2)

Blockchain is not a dependency for the 4-week pilot. It activates only after Gate A/B/C are passed and the off-chain loop is validated.

### 5.1 Token: $POLI

ERC-20 utility token. Primary uses: claim verified-read rewards, stake for premium publisher access, governance votes on treasury emission rate. The token is **not** marketed as an investment. It is a utility token under MiCA classification.

### 5.2 Smart contracts

Three contracts, deployed independently, upgradeable via OpenZeppelin Transparent Proxy.

**`PoliToken.sol`**  
Standard ERC-20. Mint function callable only by `ReadingVault`. Zero premint. No founder allocation visible in the token contract.

**`ReadingVault.sol`**  
Accepts USDC deposits from publishers. Holds USDC and $POLI reserves. Enforces on-chain rate limits: max X USDC outflow per 24h (configurable by governance). Calls `PoliToken.mint()` on validated redemptions.

**`RewardDistributor.sol`**  
Verifies ECDSA voucher signatures from the Poli-News backend server key. Checks nonce registry to prevent double-spend. Calls vault on successful verification. This is the contract the user interacts with directly. Must be audited before mainnet.

**Voucher format (off-chain → on-chain bridge):**

```json
{
  "user_address": "0x...",
  "amount_poli": 150,
  "story_id": "story_abc123",
  "nonce": "uuid-v4-unique-per-claim",
  "expiry": 1741000000,
  "server_signature": "0x<ecdsa_sig>"
}
```

### 5.3 Network strategy

| Phase | Network | Rationale |
|-------|---------|-----------|
| MVP | Ethereum Sepolia testnet | Free, EVM-compatible, widely supported |
| Phase 2 mainnet | Base (Coinbase L2) or Arbitrum | ~$0.001 per transaction vs ~$2–5 on L1 |
| Cost optimization | Solana | ~$0.00025 per transaction, large retail wallet base |
| Future | Cardano | If specific EU regulatory positioning is needed |

**Multichain strategy (no canonical bridge):** Rather than bridging the token, issue separate supply pools per chain. Each chain's `RewardDistributor` accepts vouchers signed by the same backend server key. Global supply cap is enforced off-chain by the backend. This avoids bridge exploit risk entirely.

### 5.4 Treasury flywheel

```
Publisher USDC → ReadingVault
                    │
                    ▼
Reader claims $POLI (quiz pass voucher)
                    │
                    ▼
Reader holds $POLI for premium access (demand)
  OR
Reader sells on DEX (Uniswap v3 pool: $POLI/USDC)
                    │
                    ▼
Protocol fee (0.3% swap fee) → buyback $POLI from pool
                    │
                    ▼
Price floor supported by real publisher cashflows
```

**Emission control:** Weekly emission budget is fixed in the vault. If 10,000 quiz passes occur in a week and the budget covers 5,000 $POLI, each pass earns 0.5 $POLI. Emission per user is variable; total weekly emission is capped. This mirrors the `daily_cap` already in `reward_policy_v1.md`.

**Vesting:** 50% of $POLI reward is liquid immediately. 50% vests linearly over 30 days. This reduces farming pressure and separates genuine readers from bots.

### 5.5 Tooling

| Tool | Purpose |
|------|---------|
| [Foundry](https://book.getfoundry.sh/) | Contract development, testing, deployment |
| [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts) | ERC-20 base, Proxy, AccessControl |
| [Hardhat](https://hardhat.org/) | Optional: scripting and local node for integration tests |
| [The Graph](https://thegraph.com/) | Index on-chain events for dashboard queries |
| [WalletConnect](https://walletconnect.com/) | Universal wallet connection in frontend |
| [wagmi](https://wagmi.sh/) + [viem](https://viem.sh/) | React hooks for wallet interaction |
| [Chainlink Price Feeds](https://docs.chain.link/data-feeds) | USDC/ETH price for treasury accounting |

---

## 6. Revenue Streams

Poli-News has four revenue streams. The first funds the MVP. The next three fund token value and protocol sustainability.

### 6.1 Publisher Subscription (Core)

Publishers pay a monthly fee to access the Poli-News widget and verified engagement metrics. The fee includes a USDC contribution to the treasury proportional to verified reads consumed.

**Pricing model (pilot):**
- Flat fee: EUR 500–2,000/month depending on article volume (20–200 articles)
- Variable: EUR 0.05 per verified read above a base quota
- Treasury contribution: 40% of the flat fee is deposited as USDC into `ReadingVault`

This is the only revenue stream active in the 4-week MVP.

---

### 6.2 AI Training Data Licensing

**What it is:** The reading and quiz interaction data generated on Poli-News is high-quality structured data for AI training. Specifically:
- Quiz question/answer pairs with correct labels and human-generated wrong answers
- Reading comprehension scores correlated with article topics and reading time
- User reading time distributions per topic and content type
- Structured Q&A in news domain (scarce in existing public datasets)

This data is valuable to AI labs training language models, reading comprehension models, and news-domain classifiers.

**Data schema additions (new tables, extends `data_model_mvp.sql`):**

```sql
-- Captures the full behavioral session for a single article read
CREATE TABLE reading_sessions (
  session_id      TEXT PRIMARY KEY,
  user_id         TEXT NOT NULL REFERENCES users(user_id),
  story_id        TEXT NOT NULL REFERENCES stories(story_id),
  topic_slug      TEXT NOT NULL,
  started_at      TIMESTAMP NOT NULL,
  scroll_depth    INTEGER,           -- 0–100 percent
  active_seconds  INTEGER,           -- time with tab in focus
  total_seconds   INTEGER,           -- wall-clock time
  device_type     TEXT,              -- desktop/mobile/tablet
  locale          TEXT,
  FOREIGN KEY (story_id) REFERENCES stories(story_id)
);

-- Stores each Q&A pair with outcome — the core training unit
CREATE TABLE quiz_qa_pairs (
  pair_id           TEXT PRIMARY KEY,
  story_id          TEXT NOT NULL,
  quiz_id           TEXT NOT NULL,
  question_id       TEXT NOT NULL,
  question_text     TEXT NOT NULL,
  correct_answer    TEXT NOT NULL,
  distractor_a      TEXT NOT NULL,
  distractor_b      TEXT NOT NULL,
  topic_slug        TEXT NOT NULL,
  difficulty        INTEGER,          -- 1–3
  avg_human_score   FLOAT,            -- updated rolling average
  attempt_count     INTEGER DEFAULT 0,
  created_at        TIMESTAMP NOT NULL
);

-- Per-attempt comprehension event for fine-grained behavioral data
CREATE TABLE comprehension_events (
  event_id          TEXT PRIMARY KEY,
  attempt_id        TEXT NOT NULL REFERENCES attempts(attempt_id),
  session_id        TEXT REFERENCES reading_sessions(session_id),
  question_id       TEXT NOT NULL,
  chosen_option_id  TEXT NOT NULL,
  is_correct        BOOLEAN NOT NULL,
  elapsed_ms        INTEGER NOT NULL,   -- time spent on this question
  created_at        TIMESTAMP NOT NULL
);
```

**Export pipeline:**

Data is exported as [Hugging Face Datasets](https://huggingface.co/docs/datasets/index)-compatible Parquet files. A nightly job (cron or Airflow DAG) runs:

```python
# Provider: Hugging Face Hub (free for public datasets, paid for private)
# API docs: https://huggingface.co/docs/huggingface_hub/guides/upload

from datasets import Dataset
import pandas as pd

df = pd.read_sql("""
    SELECT p.pair_id, p.story_id, p.topic_slug, p.question_text,
           p.correct_answer, p.distractor_a, p.distractor_b,
           p.difficulty, p.avg_human_score, p.attempt_count
    FROM quiz_qa_pairs p
    WHERE p.attempt_count >= 10        -- only questions with enough signal
      AND p.avg_human_score >= 0.65    -- majority of humans got it right
""", conn)

dataset = Dataset.from_pandas(df)
dataset.push_to_hub("polinews/reading-comprehension-news", private=True)
```

**Monetization options:**

| Channel | How | Estimated price |
|---------|-----|-----------------|
| Direct license to AI labs | One-time or annual data license agreement | USD 5,000–50,000 per dataset version |
| [Ocean Protocol](https://oceanprotocol.com/) | Publish dataset as a data NFT, buyers pay with OCEAN | Variable, ~USD 0.01–0.10 per sample |
| [Scale AI Data Engine](https://scale.com/data-engine) | Partner to supply domain-specific training data | Negotiated contract |
| Hugging Face private datasets | Monthly subscription for access | USD 500–2,000/month per subscriber |

**Privacy:** All exported data is pseudonymized. `user_id` is replaced with a rotating daily hash before export. No PII leaves the internal database.

---

### 6.3 Human Verification Tasks (RLHF Data Sales)

**What it is:** Some quiz questions are not standard comprehension questions — they are micro-annotation tasks designed to help AI systems learn human judgment on news content. These tasks are indistinguishable from regular quiz questions in the user's experience but generate labeled data that AI labs pay for.

**Task types:**

| Task type | User sees | AI use |
|-----------|-----------|--------|
| Summary validation | "Which of these summaries best represents the article?" | RLHF reward model training, summarization quality |
| Misinformation flag | "Does this headline accurately reflect the article body?" | Fact-checking model training, claim verification |
| Sentiment classification | "What is the overall tone of this article?" | News sentiment analysis, market signal models |
| Bias detection | "Which source perspective is represented here?" | Media bias classifiers |
| Relevance judgment | "Is this key point actually supported by the article?" | RAG retrieval quality |

**Integration into quiz flow:**

Tasks are injected transparently at the question level. The `questions` table gets a `task_type` column:

```sql
ALTER TABLE quiz_questions ADD COLUMN task_type TEXT NOT NULL DEFAULT 'comprehension';
-- Values: 'comprehension', 'detail', 'summary_validation', 'misinformation', 'sentiment', 'relevance'

ALTER TABLE quiz_questions ADD COLUMN annotation_campaign_id TEXT;
-- Links to a specific paid annotation campaign
```

**Injection rules (to preserve UX quality):**
- Max 1 annotation task per 3-question quiz set
- Annotation tasks are mixed after at least 1 standard comprehension question
- Tasks must have a plausible correct answer (not purely subjective — e.g., fact-based misinformation check)
- Tasks with `avg_human_score < 0.55` (no consensus) are flagged and excluded from the paid export

**New table:**

```sql
CREATE TABLE annotation_tasks (
  task_id           TEXT PRIMARY KEY,
  campaign_id       TEXT NOT NULL,
  question_id       TEXT NOT NULL,
  task_type         TEXT NOT NULL,
  buyer_org         TEXT,              -- e.g. 'scale_ai', 'internal', 'anthropic'
  payout_per_label  NUMERIC(10,4),     -- USD cents per valid human response
  min_labels        INTEGER DEFAULT 5, -- consensus requires N responses
  status            TEXT DEFAULT 'active',
  created_at        TIMESTAMP NOT NULL
);
```

**Data buyers and channels:**

| Buyer / Platform | What they need | Integration |
|-----------------|----------------|-------------|
| [Scale AI](https://scale.com/) | News domain Q&A, fact verification | Scale AI API — post tasks to their Human Layer, receive labeled results back |
| [Toloka](https://toloka.ai/) | Bulk annotation at low cost | Toloka API — pool of 5M+ annotators, JSON task format |
| [Surge AI](https://www.surgehq.ai/) | High-quality RLHF data | Direct API submission, audit trail |
| [Labelbox](https://labelbox.com/) | Managed annotation pipeline | Labelbox Data Rows API — export labeled datasets |
| Direct to AI labs | RLHF training pairs | Custom API or S3 data room under NDA |

**Pricing signal:** Scale AI publicly prices data annotation at USD 0.05–0.50 per task for simple classification. With 10,000 daily quiz attempts in a 200-article pilot, and 1-in-3 questions being annotation tasks, that is ~3,300 annotation events/day = ~USD 165–1,650/day at Scale pricing.

**Backend flow:**

```
Quiz is served to user
    │
    └─ question.task_type == 'annotation'?
            │
            ├─ YES → record to comprehension_events (normal)
            │        record to annotation_responses (separate)
            │        if response_count >= min_labels → compute consensus
            │        export to buyer via webhook or nightly batch
            │
            └─ NO  → standard comprehension scoring
```

---

### 6.4 Verified Attention Analytics

**What it is:** Aggregate, publisher-facing and researcher-facing analytics derived from verified reading behavior. Unlike standard analytics (pageviews, time on page) these metrics are based on confirmed comprehension — a user who passes the quiz definitively read and understood the article.

**Why it is valuable:** Traditional attention metrics (scroll depth, time on page) are easily inflated and hard to trust. A "comprehension score" derived from a quiz pass is a verified proxy for genuine engagement. Publishers can use it for editorial decisions, advertisers can pay premiums for placements on high-comprehension articles, and researchers can study news consumption.

**Metrics generated per story:**

| Metric | Formula | Notes |
|--------|---------|-------|
| `comprehension_score` | `quiz_passed / quiz_started` for that story | Verified engagement rate |
| `engagement_score` | Weighted composite: `0.4 × comprehension_score + 0.3 × avg_active_read_seconds/60 + 0.3 × comment_accept_rate` | Normalized 0–100 |
| `reading_time_p50` | Median `active_seconds` across sessions for that story | P50/P75/P95 buckets |
| `topic_interest_signal` | `quiz_started / box_viewed` grouped by topic_slug | Identifies high-interest topics per audience segment |
| `difficulty_index` | `1 - avg_human_score` across question pool | Low-difficulty articles score near 0 |
| `return_uplift` | 7-day return rate of users who passed quiz vs. those who did not | Requires cohort comparison |
| `quality_comment_rate` | `comment_accepted / comment_submitted` | Content resonance signal |

**Analytics tables (new):**

```sql
-- Pre-aggregated daily story-level metrics (refresh every 15 min during pilot)
CREATE TABLE story_analytics (
  analytics_id        TEXT PRIMARY KEY,
  story_id            TEXT NOT NULL REFERENCES stories(story_id),
  date                DATE NOT NULL,
  box_viewed          INTEGER DEFAULT 0,
  quiz_started        INTEGER DEFAULT 0,
  quiz_passed         INTEGER DEFAULT 0,
  comment_submitted   INTEGER DEFAULT 0,
  comment_accepted    INTEGER DEFAULT 0,
  avg_active_seconds  FLOAT,
  avg_scroll_depth    FLOAT,
  comprehension_score FLOAT,
  engagement_score    FLOAT,
  UNIQUE (story_id, date)
);

-- Topic-level weekly signals for trend analysis and research export
CREATE TABLE topic_interest_weekly (
  week_start          DATE NOT NULL,
  topic_slug          TEXT NOT NULL,
  locale              TEXT NOT NULL,
  attempt_rate        FLOAT,    -- quiz_started / box_viewed
  comprehension_score FLOAT,
  avg_read_seconds    FLOAT,
  unique_readers      INTEGER,
  PRIMARY KEY (week_start, topic_slug, locale)
);
```

**Analytics API (adds to `api_contract_mvp.md`):**

```
GET /analytics/story/:story_id
  → comprehension_score, engagement_score, reading_time_p50, difficulty_index
  → Requires: publisher API key

GET /analytics/topic/:topic_slug?locale=en-US&from=2026-03-01&to=2026-03-14
  → Weekly topic_interest_signals, comprehension trend, unique reader count
  → Requires: publisher or researcher API key

GET /analytics/publisher/benchmark
  → Publisher's stories vs platform median across same topic/locale
  → Requires: publisher API key

GET /analytics/export?format=parquet&from=...&to=...
  → Full attention dataset export for licensed researchers
  → Requires: data license agreement + API key
```

**Monetization options:**

| Tier | What | Price |
|------|------|-------|
| Publisher Standard | Story-level comprehension + engagement in dashboard (included in publisher sub) | Bundled |
| Publisher Premium | Topic benchmark, audience segmentation, week-over-week trend | +EUR 200/month |
| Researcher License | Full anonymized dataset export via API or S3 | EUR 500–5,000 per export |
| Advertiser Attention Verification | Prove their ad was placed on a verified-comprehension article | EUR 0.10–0.50 per verified impression |

**Analytics backend stack:**

For MVP, PostgreSQL with materialized views refreshed every 15 minutes is sufficient. At scale (Phase 2), migrate aggregation to:
- [ClickHouse](https://clickhouse.com/) — columnar DB, handles billions of events, free self-hosted
- [TimescaleDB](https://www.timescale.com/) — PostgreSQL extension for time-series, minimal migration cost
- [Apache Superset](https://superset.apache.org/) — open-source BI for researcher-facing dashboards

---

## 7. Token Economics ($POLI)

### 7.1 Supply

| Parameter | Value |
|-----------|-------|
| Token name | Poli |
| Ticker | $POLI |
| Max supply | 100,000,000 (100M) |
| Initial circulating supply | 0 (no premint) |
| Emission mechanism | Earned only by verified readers |
| Emission rate | Fixed weekly budget set by treasury governance |

### 7.2 Value support (the three pillars)

The token has real value because three independent cashflows buy or hold it:

1. **Publisher payments** → treasury USDC → buys $POLI to reward readers → demand
2. **AI data licensing revenue** → treasury USDC → same buyback mechanism → demand
3. **Human annotation payments** → treasury USDC → same → demand

This means token price is not purely speculative — it is proportional to the platform's total verified-read volume and data revenue.

### 7.3 Anti-death-spiral mechanics

| Mechanism | How |
|-----------|-----|
| Weekly emission cap | Total weekly $POLI is fixed; more readers = less per reader |
| 50% vesting (30-day) | Reduces immediate sell pressure |
| Utility hold incentive | Staking $POLI grants premium access without redeeming |
| Buyback floor | 20% of all protocol revenue is auto-deployed for buybacks |
| New user multiplier | 0.3× for first 7 days — reduces farming ROI |

### 7.4 Redemption options (Phase 2)

- Subscription discount coupon (burn $POLI, receive USDC coupon)
- 24h premium access (time-lock $POLI, release after period)
- Governance vote weight (1 $POLI = 1 vote on emission rate changes)
- Data access pass (stake $POLI for researcher API access)

---

## 8. Data Model

See `specs/data_model_mvp.sql` for the full schema. Summary of tables:

| Table | Purpose |
|-------|---------|
| `users` | Profile, reputation score, onboarding state |
| `feed_items_raw` | Raw RSS items as ingested |
| `stories` | Normalized story records with topic and source mapping |
| `story_sources` | Source attribution per story (name, URL, domain) |
| `quizzes` | Question pools per story |
| `quiz_questions` | Individual questions (extended with `task_type`, `annotation_campaign_id`) |
| `attempts` | Quiz submission records with score, timing, pass/fail |
| `comments` | Comment submissions with quality status |
| `rewards_ledger` | Append-only credit/debit/revoke log |
| `fraud_signals` | Anomaly flags with severity, reason, review state |
| `reading_sessions` | Behavioral session data per article read *(new)* |
| `quiz_qa_pairs` | Structured Q&A pairs for AI export *(new)* |
| `comprehension_events` | Per-question timing and correctness *(new)* |
| `annotation_tasks` | Annotation campaign tracking *(new)* |
| `story_analytics` | Pre-aggregated engagement metrics *(new)* |
| `topic_interest_weekly` | Weekly topic signal aggregates *(new)* |

---

## 9. API Reference

Full request/response shapes in `specs/api_contract_mvp.md`. Summary:

### Content

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/feed?topic=&page=` | Paginated story feed by topic |
| GET | `/stories/:story_id` | Story page payload with quiz availability |

### Verification & Rewards

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/quiz?story_id=` | Randomized quiz for a story |
| POST | `/attempt` | Submit quiz answers, receive pass/score/credits |
| POST | `/comment` | Submit quality comment for bonus credits |
| GET | `/balance` | Current and pending balance, recent transactions |
| POST | `/redeem` | Redeem credits for a reward (idempotent) |

### Publisher & Analytics

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/publisher-dashboard` | Core KPIs: funnel, quality, economics, fraud |
| GET | `/analytics/story/:story_id` | Story-level attention metrics |
| GET | `/analytics/topic/:slug` | Topic-level weekly signals |
| GET | `/analytics/export` | Bulk dataset export (licensed users) |

### Blockchain (Phase 2)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/voucher/issue` | Issue a signed redemption voucher for on-chain claim |
| GET | `/voucher/status/:nonce` | Check if a voucher has been consumed on-chain |

---

## 10. Feed Registry

30 active feeds across 3 locales. Naming convention frozen: `feed_<topic>_<country>`.

Coverage: all 10 topic slugs × 3 locales (US, UK, IT). Full list in `specs/feed_registry_v1.csv`.

**Freeze rule (effective 2026-03-14):** New feeds or modifications are only allowed at scheduled checkpoints. URL changes are not required when current feeds are valid.

---

## 11. Anti-Fraud System

The MVP goal is not zero fraud — it is making farming economically unprofitable and operationally manageable.

### Baseline defenses

- Rate limiting per account, session, and device fingerprint (Redis counters)
- Cooldown between attempts (120s, enforced backend)
- Max 3 attempts per story per day
- One reward per story per account (enforced at ledger write with `UNIQUE(user_id, story_id)` constraint)
- New-user multiplier: 0.3× for first 7 days
- Minimum elapsed time threshold per attempt (rejects bots answering in <8s)

### Abuse signals and responses

| Signal | Detection | Response |
|--------|-----------|----------|
| Too-fast attempts | `elapsed_seconds < 8` | Reject + temporary block |
| Mass new accounts | Device/IP cluster in `fraud_signals` | Multiplier + onboarding cap |
| Copied comments | Text similarity hash (MinHash) | Dedup + manual review |
| API burst | Requests/minute spike per IP | Rate limit + challenge |
| Multi-account same story | Correlation flags in `fraud_signals` | Enforce 1-reward constraint |
| Bots on endpoints | Uniform user-agent pattern | Adaptive throttle |

### Review SOP

Daily review at 14:00 (see `runbooks/antifraud_review_runbook_v1.md`). Emergency review within 2h for critical spikes (>5 high-severity signals in 60 min).

Allowed reason codes for revocation: `too_fast_attempts`, `duplicate_pattern`, `multi_account_cluster`, `cooldown_bypass`, `redeem_spike`.

---

## 12. KPI Framework

### Primary KPIs

| KPI | Formula | Target | Alert threshold |
|-----|---------|--------|-----------------|
| Attempt rate | `quiz_started / box_viewed` | 15–25% | <12% for 2 days |
| Pass rate | `quiz_passed / quiz_started` | 60–80% | <50% for 2 days |
| Avg quiz time | Mean `elapsed_seconds` on valid attempts | 20–60s | <12s or >90s |
| Verified read cost | `(net_credits + review_cost) / verified_reads` | Within publisher threshold | >budget for 2 days |
| Fraud flag rate | `fraud_signals / attempts` | Manageable | >defined threshold |
| Redemption rate | `redeem_users / users_with_credits` | Monitor trend | Spike >2× baseline |

### New KPIs (added with data revenue layer)

| KPI | Formula | Target |
|-----|---------|--------|
| Annotation task yield | `annotation_responses / annotation_tasks_served` | >80% valid labels per task |
| Dataset export quality | `pairs_with_consensus / total_pairs` (consensus = ≥70% agree) | >75% |
| Engagement score avg | Mean `engagement_score` across active stories | >40/100 |
| Data revenue per verified read | `(annotation_revenue + analytics_revenue) / verified_reads` | Track trend |

### Dashboard refresh SLA

- All KPIs update every 15 minutes during pilot hours
- Daily KPI report generated by 19:00
- Publisher dashboard via `GET /publisher-dashboard`

---

## 13. Pilot Plan & Decision Gates

### Timeline

| Phase | Days | Objective | Output |
|-------|------|-----------|--------|
| Pre-launch | 1–7 | Technical integration, QA, quiz pool | Widget live on staging |
| Controlled launch | 8–14 | 10–20% traffic, threshold calibration | Anti-fraud baselines set |
| Full run | 15–26 | KPI collection, daily reports | Dashboard live |
| Decision window | 27–30 | Gate evaluation, go/no-go decision | Decision memo |

### Decision gates

| Gate | Condition | Pass criteria |
|------|-----------|---------------|
| A — Usability | Attempt rate + pass rate | Both within target range |
| B — Sustainability | Verified read cost | Within publisher-agreed threshold |
| C — Risk | Fraud queue | No unresolved critical spikes >24h |

### Possible outcomes

- **Go:** Expand to more articles, activate Phase 2 blockchain, begin data licensing discussions
- **Conditional Go:** One gate misses but trend is improving — second pilot cycle with tuned parameters
- **No-Go:** Suspend rewards, analyze root cause, pivot mechanic if needed

---

## 14. Tech Stack & Provider Reference

### Backend

| Component | Technology | Notes |
|-----------|-----------|-------|
| API | FastAPI (Python) or Node.js + Hono | FastAPI preferred for ML/data pipeline integration |
| Database | PostgreSQL 16 | Main transactional + analytics store |
| Cache / Rate limiting | Redis (Upstash for serverless) | Attempt counters, session state |
| Queue | BullMQ (Redis) or Celery (Python) | Ingestion jobs, quiz generation jobs |
| File storage | Cloudflare R2 or AWS S3 | Dataset exports, Parquet files |
| Auth | Clerk or Lucia Auth | Magic link + JWT sessions |

### AI / ML

| Use | Provider | Model | Estimated cost |
|-----|----------|-------|----------------|
| Quiz pool generation | OpenAI | `gpt-4o-mini` | ~$0.001/story |
| Key point generation | OpenAI | `gpt-4o-mini` | ~$0.001/story |
| Comment spam detection | FastText or `mistral-7b` self-hosted | Open source | Minimal |
| Annotation task generation | OpenAI | `gpt-4o` | ~$0.005/task batch |
| Dataset embeddings (for dedup) | OpenAI | `text-embedding-3-small` | ~$0.0001/1K tokens |

### Blockchain

| Component | Tool | Docs |
|-----------|------|------|
| Contract development | Foundry | https://book.getfoundry.sh |
| ERC-20 base | OpenZeppelin Contracts v5 | https://docs.openzeppelin.com/contracts/5.x |
| Testnet | Ethereum Sepolia | https://sepolia.etherscan.io |
| L2 mainnet | Base | https://docs.base.org |
| Wallet connection | WalletConnect v2 + wagmi | https://docs.walletconnect.com |
| Onchain indexing | The Graph | https://thegraph.com/docs |
| Price feeds | Chainlink | https://docs.chain.link/data-feeds |

### Analytics

| Component | Tool | Notes |
|-----------|------|-------|
| MVP analytics DB | PostgreSQL materialized views | Refresh every 15 min |
| Phase 2 analytics | ClickHouse (self-hosted) or Tinybird | Columnar, handles 1B+ events |
| BI / dashboards | Metabase or Apache Superset | Open source, self-hosted |
| Data export format | Parquet (Apache Arrow) | Standard for AI training datasets |
| Dataset hosting | Hugging Face Hub | Private datasets, versioned |

### Data marketplace

| Channel | Docs |
|---------|------|
| Ocean Protocol | https://docs.oceanprotocol.com |
| Scale AI Data Engine | https://scale.com/data-engine |
| Toloka | https://toloka.ai/docs/api |
| Labelbox | https://docs.labelbox.com |

---

## 15. Compliance Notes

### GDPR / Privacy

- All personal data stored in EU-region infrastructure (or with EU-resident processor)
- Reading behavior data pseudonymized before export (`user_id` replaced with rotating daily hash)
- Users have the right to request deletion of their reading history — `DELETE /user/data` endpoint required before pilot goes live
- Magic link auth never stores passwords; sessions expire after 7 days

### MiCA (EU Crypto Asset Regulation, applicable from Dec 2024)

- $POLI is structured as a **utility token**: its primary purpose is accessing editorial features (premium access, governance), not investment
- The token is not marketed as a yield-bearing instrument
- Whitepaper must clearly state: no guarantee of token value, token is not a security, no dividends or interest payments
- Phase 2 legal review required before mainnet deployment in any EU country

### Attribution

- Every story page must display: original source name, outbound link to source article, publish timestamp, and the label *"Summary generated by Poli-News from public source metadata"*
- No full-text copy of source articles
- No reproduction of paywalled content
- Source block must appear above the quiz box (enforced in `story_template_v1.md`)

### AI annotation data

- Users are informed in the terms of service that quiz interactions may be used to improve AI systems
- No biometric or sensitive category data is collected
- Annotation data exported to third parties is subject to a Data Processing Agreement (DPA)

---

## Stop Conditions

These conditions trigger automatic suspension — no human decision required:

| Condition | Action |
|-----------|--------|
| Fraud spike: >N critical signals unresolved >24h | Pause all reward issuance |
| Ingestion failure: stale mode active >defined window | Pause new traffic |
| Ledger inconsistency: balance check fails | Pause redemption immediately |
| Treasury drawdown: daily outflow cap hit | Pause $POLI claims on-chain |

---

## Evidence Pack (required by Day 28)

- [ ] `topics_v1` — frozen ✓
- [ ] `feed_registry_v1` — frozen ✓
- [ ] `ingestion_policy_v1` — written ✓
- [ ] `source_policy_v1` — written ✓
- [ ] `story_template_v1` — written ✓
- [ ] `quiz_spec_v1` — written ✓
- [ ] `reward_policy_v1` — written ✓
- [ ] `kpi_spec_v1` — written ✓
- [ ] `data_model_mvp.sql` (extended with data layer tables) — written ✓
- [ ] API test report
- [ ] Load/performance report
- [ ] Fraud simulation log (7 scenarios)
- [ ] Decision memo: `GO | CONDITIONAL_GO | NO_GO`
- [ ] First dataset export sample (quiz_qa_pairs)
- [ ] Annotation task pilot results

---

*Poli-News — v0.2 — 2026-03-14 — Off-Chain MVP + Blockchain Revenue Model*
