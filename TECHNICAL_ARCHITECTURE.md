# Poli-News Technical Architecture
## Complete System Design & Maturity Assessment

**Version:** 0.3.0 (MVP Off-Chain)  
**Last Updated:** 2026-03-19  
**Status:** Alpha - Core pipeline functional, missing critical components for production

---

## 📊 Executive Summary

**Poli-News** is a **Proof-of-Reading Incentive Layer** that monetizes verified reading comprehension. The system fetches news articles from 30 RSS feeds, normalizes them, generates AI-powered comprehension quizzes, and rewards users with $POLI tokens.

### Key Characteristics
- **Type:** FastAPI-based backend + background worker
- **Primary Language:** Python 3.11+
- **Database:** SQLite (dev/staging) - NOT production ready
- **LLM Integration:** Ollama (local) or OpenAI (cloud)
- **Auth:** Magic links + JWT
- **Deployment:** Single-process or multi-process (API + worker separated)

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                             │
│                  (Mobile App / Web Frontend)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS REST API
┌────────────────────────▼────────────────────────────────────────┐
│                      API SERVER LAYER                            │
│  (FastAPI on 0.0.0.0:8000)                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Routes:                                                   │   │
│  │ • /auth           (magic link + JWT)                     │   │
│  │ • /feed           (paginated story feed by topic)        │   │
│  │ • /stories/{id}   (full story + key points + sources)    │   │
│  │ • /quiz           (randomized questions)                 │   │
│  │ • /attempt        (submit answers + fraud checks)        │   │
│  │ • /balance        (user reward balance + ledger)         │   │
│  │ • /comment        (post reading comments)                │   │
│  │ • /dashboard      (personal stats + achievements)        │   │
│  │ • /analytics      (publisher KPI dashboard)              │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │ SQLite Connection
┌────────────────────────▼────────────────────────────────────────┐
│                    DATA LAYER (SQLite)                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Ingestion Tables:                                        │   │
│  │ • feed_items_raw        (raw RSS items)                  │   │
│  │ • dedup_registry        (24h dedup window)               │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Story Tables:                                            │   │
│  │ • stories               (normalized articles)            │   │
│  │ • story_sources         (multi-source attribution)       │   │
│  │ • story_key_points      (LLM-generated summaries)        │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ Quiz Tables:                                             │   │
│  │ • quizzes               (question pools)                 │   │
│  │ • quiz_questions        (N questions per quiz)           │   │
│  │ • attempts              (user answers + scoring)         │   │
│  │ • attempt_answers       (detailed answer log)            │   │
│  ├──────────────────────────────────────────────────────────┤   │
│  │ User & Reward Tables:                                    │   │
│  │ • users                 (profile + reputation)           │   │
│  │ • sessions              (JWT session tracking)           │   │
│  │ • rewards_ledger        (all credit transactions)        │   │
│  │ • comments              (user-generated content)         │   │
│  │ • anti_fraud_log        (suspicious activity)            │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │ Polling every 15 minutes
┌────────────────────────▼────────────────────────────────────────┐
│                 BACKGROUND WORKER LAYER                          │
│           (APScheduler-based pipeline orchestration)             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Pipeline Stages (sequential):                            │   │
│  │ 1. RSS Collector       (fetch + parse from 30 feeds)    │   │
│  │ 2. Normalizer          (clean, dedupe, validate)        │   │
│  │ 3. Keypoints Gen       (LLM summarization)              │   │
│  │ 4. Quiz Pool Gen       (LLM question generation)        │   │
│  │ 5. Analytics Job       (compute KPIs + metrics)         │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                  EXTERNAL DEPENDENCIES                           │
│  • Google News RSS (30 feeds, US/UK/IT)                          │
│  • Ollama / OpenAI (LLM for keypoints + quizzes)                 │
│  • Resend API (optional email delivery for magic links)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📁 Folder Structure & Responsibilities

### `polinews/` (Root Package)
Main application entry point. Contains configuration, top-level modules, and subpackages.

#### Key Files:
- **`config.py`** — Unified configuration from environment variables
  - DB path, API host/port, LLM settings (Ollama vs OpenAI)
  - Collector timeout/retry settings, dedup window, feed registry path
  - Auth secrets (JWT key), magic link expiry
  - All settings respect `.env` file overrides
  
- **`main.py`** — Entry points for CLI commands
  - `polinews-serve` → starts FastAPI server (uvicorn)
  - `polinews-collect` → starts blocking scheduler worker

- **`__init__.py`** — Package marker

---

### `polinews/api/` - REST API Layer (FastAPI)
**Responsibility:** Expose REST endpoints for client apps (mobile, web)  
**Development Status:** ~70% complete (core endpoints working, some features stub)

#### Files & Endpoints:

1. **`app.py`** — FastAPI application factory + middleware setup
   - Creates FastAPI instance with CORS middleware
   - Mounts all routers (auth, feed, story, quiz, rewards, dashboard, analytics, sessions)
   - Lifespan events: DB schema verification, optional in-process scheduler
   - Health check endpoint (`/health`)

2. **`auth.py`** — Authentication & user management (prefix: `/auth`)
   - **POST /auth/magic-link** — Request magic link email
     - Input: `{email: string, base_url: string}`
     - Creates/retrieves user, generates time-limited token, sends via Resend or logs
     - Output: `{status: "link_sent"}`
   - **POST /auth/verify** — Exchange magic link token for JWT
     - Input: `{token: string}`
     - Validates token expiry, issues 7-day JWT
     - Output: `{access_token: string, user_id: string, email: string}`
   - **GET /auth/me** — Get current authenticated user profile
     - Output: `{user_id, email, created_at, reputation, onboarding_state}`
   - **Dependencies:** `get_current_user()` (used by all protected routes), `get_optional_user()`

3. **`feed_story.py`** — Story & feed retrieval (prefixes: `/feed`, `/stories`)
   - **GET /feed?topic={politics|economy|...}&page=1&limit=20**
     - Returns paginated story list for a topic
     - Output: `{items: [FeedItem], topic_slug, page, limit, has_next}`
     - DB query filters: `stories.status = 'publishable'` only
   - **GET /stories/{story_id}** — Fetch full story with key points & sources
     - Validates story has ≥3 key points and ≥1 source (runtime minimum)
     - Output: `{story_id, headline, summary, key_points[], sources[], quiz_available}`
   - **DB Dependencies:** `stories`, `story_key_points`, `story_sources` tables

4. **`quiz.py`** — Quiz engine & answer evaluation (prefix: `/quiz`)
   - **GET /quiz?story_id={id}** — Fetch randomized question set
     - Enforces 3 attempts/day limit + 2-min cooldown
     - Returns questions WITHOUT correct_option_id (anti-cheating)
     - Output: `{quiz_id, story_id, questions: [{question_id, text, options: [{option_id, text}]}], attempts_remaining, cooldown_seconds}`
   - **POST /quiz/attempt** — Submit answers & get scored
     - Inputs: `{quiz_id, story_id, answers: [{question_id, chosen_option_id}], client_elapsed_seconds}`
     - Validation: ≥70% pass threshold, ≥8 sec elapsed (anti-bot)
     - Fraud checks: detects repeat patterns, temporal anomalies
     - Reward logic: base 10 credits + 5 for comment + daily cap 50
     - New users (first 7 days) earn 30% multiplier
     - Output: `{passed: bool, score_percent: int, credits_awarded: int, balance_preview, cooldown_seconds, attempts_remaining}`
   - **DB Dependencies:** `quizzes`, `quiz_questions`, `attempts`, `attempt_answers`, `rewards_ledger`, `anti_fraud_log`

5. **`rewards.py`** — User balance & social features (prefix: `/rewards`)
   - **GET /balance** — Current user balance + ledger
     - Output: `{current_balance, pending_balance, credits_earned_today, daily_cap, recent_transactions: [LedgerEntry]}`
   - **POST /comments** — Post reading comment
     - Inputs: `{story_id, text: string (50-1000 chars)}`
     - Bonus: +5 credits (provisional, confirmed after manual review)
     - Output: `{accepted: bool, review_status, credits_provisional, comment_id}`
   - **DB Dependencies:** `rewards_ledger`, `comments`

6. **`dashboard.py`** — Personal analytics dashboard
   - **GET /dashboard** — User stats (readings, quiz pass rate, earnings, achievements)
   - **Status:** Stub, not fully implemented

7. **`sessions.py`** — Session management
   - **GET /sessions** — List active JWT sessions
   - **POST /sessions/logout** — Revoke session (optional, JWT doesn't support server-side revocation in MVP)
   - **Status:** Minimal, mostly stub

8. **`analytics.py`** — Publisher-facing KPI dashboard
   - **GET /analytics/publisher** — Aggregate metrics per publisher
   - **Status:** Stub, not fully implemented

#### Auth Dependencies:
- Magic link tokens checked for expiry + signature
- JWT tokens verified with HS256 algorithm
- All protected routes use `Depends(get_current_user)` or `Depends(get_optional_user)`

---

### `polinews/auth/` - Authentication Utilities
**Responsibility:** JWT + magic link token generation/validation  
**Development Status:** ~80% complete (core logic solid, edge cases possible)

1. **`jwt.py`** — JWT token creation & validation
   ```python
   create_token(user_id: str, email: str, expire_days: int) -> str
   decode_token(token: str) -> dict[user_id, email]  # raises JWTError
   ```
   - Algorithm: HS256 (symmetric key from `JWT_SECRET_KEY`)
   - Includes `exp`, `sub` (user_id), `email` claims
   - Default expiry: 7 days

2. **`magic_link.py`** — One-time magic link token for passwordless auth
   ```python
   generate_token() -> str  # 32-byte random hex
   is_expired(token: str, created_at: str, expire_minutes: int) -> bool
   send_magic_link(email: str, token: str, base_url: str) -> bool
   ```
   - Delivery mode: `"log"` (stdout) or `"resend"` (Resend API)
   - Token stored in DB associated with email
   - Default expiry: 15 minutes

---

### `polinews/collector/` - RSS Ingestion & Data Processing Pipeline
**Responsibility:** Fetch, parse, normalize, deduplicate, and enrich news articles  
**Development Status:** ~60% complete (core stages work, some edge cases incomplete)

#### High-Level Pipeline
```
RSS Feeds (30)
      ↓
  Collector (fetch + parse)
      ↓
  feed_items_raw (3000-4000 items per cycle)
      ↓
  Normalizer (clean, validate, deduplicate)
      ↓
  stories (normalized, validated)
      ↓
  Keypoints Generator (LLM)
      ↓
  story_key_points (3-5 bullet points per story)
      ↓
  Quiz Pool Generator (LLM)
      ↓
  quizzes + quiz_questions (2-3 questions per story, 70% pass_threshold)
      ↓
  Publishable Stories (ready for API)
```

#### Key Files:

1. **`rss_collector.py`** — Fetch & parse RSS feeds
   - **Entry point:** `run_once(feeds_csv, db_path, log_dir, state_path)`
   - Process per feed:
     1. Load active feeds from CSV (30 default)
     2. `fetch_with_retry(url)` — HTTP GET with exponential backoff (1s, 3s, 9s)
     3. `parse_feed(xml)` — Parse RSS/Atom XML → list of `ParsedItem`
     4. Validate items (has title, link, source) — reject if not
     5. Insert accepted items into `feed_items_raw` table
   - **Output artifacts:** `feed_items_raw` table, `ingestion_runs.log`, `ingestion_rejects.log`
   - **Execution time:** ~50s for 30 feeds (3031 items)
   - **Error handling:** Logs fetch errors, parse errors separately

2. **`parser.py`** — XML RSS/Atom parsing
   - `parse_feed(xml_payload: bytes) -> list[ParsedItem]`
   - Handles both RSS 2.0 and Atom 1.0 feeds from Google News
   - Extracts: title, link, snippet, source_name, source_url, published_at, payload (full XML node)
   - **Status:** Functional but lacks edge case handling for malformed feeds

3. **`normalizer.py`** — Clean, validate, deduplicate & resolve canonical URLs
   - **Entry point:** `run_once(db_path, feeds_csv, topics_file, log_dir, dedup_window_hours, ...)`
   - Process:
     1. Read `feed_items_raw` → fetch & clean text
     2. Extract snippet from summary/description/content fields
     3. Resolve canonical URL for each source (follows HTTP 30x, extracts og:url meta)
     4. Build dedup key: `sha1(title_fingerprint | domain | url | time_bucket)`
     5. Check if dedup_key exists (24h window) → skip if duplicate
     6. Create `stories` record (per unique story ID across multiple sources)
     7. Create `story_sources` records (per source URL)
   - **Key concept:** One story can have multiple sources (aggregation)
   - **Dedup window:** 24 hours (configurable)
   - **Topic mapping:** Feed CSV contains topic_slug → story.topic_slug
   - **Status:** CRITICAL ISSUE — normalizer not running in production (see Issues section)

4. **`dedup.py`** — Deduplication logic
   - `build_title_fingerprint(title)` — normalize to lowercase alphanumeric
   - `build_dedup_key(title_fingerprint, publisher_domain, url, published_at, window_hours)` → sha1 digest
   - `is_duplicate(conn, dedup_key)` — check `dedup_registry` table
   - Window-based dedup: items published within same 24h bucket considered for dedup

5. **`keypoints_generator.py`** — LLM-powered summarization
   - **Entry point:** `run_once(db_path, ollama_base_url, model, timeout_seconds, max_stories, ...)`
   - Process:
     1. Find stories without keypoints (`keypoints_generated_at IS NULL`)
     2. For each story, call LLM with story headline + summary
     3. LLM prompt: "Extract 3-5 key points from this article"
     4. Parse response → insert into `story_key_points` table
     5. Update story publishability based on keypoint success
   - **LLM Options:**
     - Ollama (local, default): `http://localhost:11434/api/generate`
     - OpenAI (cloud): `https://api.openai.com/v1/chat/completions`
   - **Default model:** qwen2.5:3b (Ollama) or gpt-4o-mini (OpenAI)
   - **Timeout:** 25 seconds per request
   - **Max stories per run:** 150 (configurable)
   - **Status:** Functional but slow (25s/request)

6. **`quiz_pool_generator.py`** — LLM-powered quiz generation
   - **Entry point:** `run_once(db_path, ollama_base_url, model, max_stories, target_size, ...)`
   - Similar to keypoints, but generates quiz questions instead
   - **Question structure:** 2-3 questions per story, multiple choice (4 options)
   - **Prompt:** "Generate N quiz questions to test understanding of this article"
   - **Key constraint:** question difficulty should challenge readers (not trivial)
   - **Quiz status:** `quiz_status` enum (quiz_available, quiz_failed_generation, etc.)
   - **Pass threshold:** 70% correct (configurable)
   - **Status:** Functional but question quality depends on LLM

7. **`canonical_url.py`** — URL canonicalization & resolution
   - `normalize_canonical_url(url)` — parse + reconstruct canonical form
   - `resolve_canonical_url(url)` — follow HTTP 30x redirects, extract og:url meta tag
   - Used to detect when same article is published at multiple URLs (same content)

8. **`db.py`** — Collector-specific DB operations
   - Helper functions to insert/fetch from ingestion tables
   - Separated from main `polinews/db/` to avoid circular imports
   - Functions: `connect_db()`, `insert_feed_item_raw()`, `fetch_feed_items_raw()`, `insert_story()`, `insert_dedup_registry()`, etc.

9. **`config.py`** — Collector-specific configuration
   - Reads from environment, mirrors settings in `polinews/config.py`
   - Allows independent override of collector timeout/retry settings

10. **`collector_logging.py`** — Structured logging for collector runs
    - `CollectorLogger` class wraps CSV-based logging
    - Logs: run_id, start/end time, item counts, error class
    - Used to track pipeline health over time

11. **`README.md`** — Documentation for running collector stages manually
    - CLI examples for each stage (rss_collector, normalizer, keypoints_gen, quiz_pool_gen)

---

### `polinews/db/` - Database Schema & Connection Management
**Responsibility:** Database setup, schema versioning, connection pooling  
**Development Status:** ~90% complete (schema solid, migrations basic)

1. **`schema.py`** — SQLite schema definition
   - **Key principle:** `ensure_schema(conn)` is idempotent (safe to call every startup)
   - **Tables:**
     - **Ingestion:** `feed_items_raw`, `dedup_registry`
     - **Story:** `stories`, `story_sources`, `story_key_points`
     - **Quiz:** `quizzes`, `quiz_questions`, `attempts`, `attempt_answers`
     - **User:** `users`, `sessions`
     - **Reward:** `rewards_ledger`, `comments`
     - **Metrics:** `anti_fraud_log`, `analytics_snapshots`
   - **Migrations:** Basic ALTER TABLE support for backward compatibility
   - **Indexes:** Optimized for common queries (topic_published, status, story_id)

2. **`connection.py`** — Connection factory & pool management
   - `connect_db(db_path: Path) -> sqlite3.Connection`
   - Sets row factory to `sqlite3.Row` (dict-like access)
   - Enables FOREIGN KEY constraints
   - Single connection per call (no connection pooling yet — limitation for production)

---

### `polinews/worker/` - Background Job Orchestration
**Responsibility:** Schedule & execute the 5-stage ingestion pipeline every 15 minutes  
**Development Status:** ~50% complete (pipeline structure works, scheduler robustness needs work)

1. **`scheduler.py`** — APScheduler-based pipeline orchestration
   - **Pipeline stages (executed sequentially):**
     1. `_run_collect()` — RSS collector
     2. `_run_normalize()` — Normalizer
     3. `_run_keypoints()` — Keypoints generator (LLM)
     4. `_run_quiz_pool()` — Quiz generator (LLM)
     5. `_run_analytics()` — Compute KPIs
   - **Schedule:** Every `COLLECTOR_INTERVAL_MINUTES` (default: 15 min)
   - **Jitter:** Random 0-30 second delay to avoid thundering herd
   - **Error handling:** Each stage catches exceptions & logs (pipeline continues on error)
   - **Entry points:**
     - `start_blocking_scheduler()` → used by `polinews-collect` CLI (blocks process)
     - `make_background_scheduler()` → embedded in FastAPI lifespan (runs in background)
   - **Status:** Functional but lacks monitoring/alerting

2. **`analytics_job.py`** — Compute aggregated metrics
   - Runs after quiz generation
   - Aggregates: total stories published, average quiz pass rate, daily active users, token distribution, etc.
   - **Status:** Stub, mostly placeholder

---

## 🗄️ Database Schema Summary

### Core Tables (9 tables + indexes)

#### Ingestion Pipeline
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `feed_items_raw` | Raw RSS items before normalization | raw_id, feed_id, fetched_at, title, snippet, source_name, source_url, published_at, payload_json |
| `dedup_registry` | 24-hour deduplication window | dedup_key (PK), story_id (FK), raw_id, created_at |

#### Story Management
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `stories` | Normalized article records | story_id (PK), topic_slug, headline, summary, published_at, status, quiz_status, keypoints_generated_at, quiz_updated_at |
| `story_sources` | Multi-source attribution | story_source_id (PK), story_id (FK), source_name, source_url, canonical_url, publisher_domain |
| `story_key_points` | LLM-generated keypoints | key_point_id (PK), story_id (FK), position, text, created_at |

#### Quiz System
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `quizzes` | Question pool metadata | quiz_id (PK), story_id (FK), version, question_pool_size, pool_signature, generator_version, created_at |
| `quiz_questions` | Individual questions | question_id (PK), quiz_id (FK), question_text, task_type, options_json, correct_option_id, created_at |
| `attempts` | User quiz submissions | attempt_id (PK), user_id (FK), quiz_id (FK), story_id (FK), passed, score_percent, credits_awarded, elapsed_seconds, created_at |
| `attempt_answers` | Detailed answer records | answer_id (PK), attempt_id (FK), question_id (FK), chosen_option_id, is_correct, created_at |

#### User & Rewards
| Table | Purpose | Key Fields |
|-------|---------|-----------|
| `users` | User profiles | user_id (PK), email (UNIQUE), reputation, onboarding_state, created_at |
| `sessions` | JWT session tracking | session_id (PK), user_id (FK), claims_json, issued_at, expires_at |
| `rewards_ledger` | All credit transactions | entry_id (PK), user_id (FK), delta_credits, reason, story_id (FK), reference_id, created_at |
| `comments` | User-generated content | comment_id (PK), user_id (FK), story_id (FK), text, review_status, created_at |
| `anti_fraud_log` | Suspicious activity | log_id (PK), user_id (FK), reason_code, attempt_ids, created_at |

---

## 🔄 Data Flow & Interactions

### 1. **Reader Authentication Flow**
```
Client POST /auth/magic-link {email}
    ↓
[Server creates/retrieves user, generates 15-min token]
    ↓
Database: users table INSERT or SELECT
    ↓
Email delivery (Resend API or stdout log)
    ↓
Client receives email with link {base_url}?token={magic_link_token}
    ↓
Client POST /auth/verify {token}
    ↓
[Server validates token expiry, signs JWT]
    ↓
Response: {access_token, user_id, email}
    ↓
Client stores JWT in localStorage/secureStorage
    ↓
Subsequent requests use Authorization: Bearer {JWT}
```

### 2. **Story Feed Flow**
```
Client GET /feed?topic=politics&page=1
    ↓
[Server validates topic from enum, offset from page]
    ↓
Database: SELECT FROM stories WHERE topic_slug = ? AND status = 'publishable'
    ↓
For each story:
  - Fetch 3-5 key_points FROM story_key_points
  - Check quiz_status (quiz_available ?)
  - Format FeedItem response (headline, summary[:160], source_count)
    ↓
Response: {items: [FeedItem], page, limit, has_next}
```

### 3. **Quiz Attempt Flow**
```
Client GET /quiz?story_id={id}
    ↓
[Server checks attempts_remaining (max 3/day)]
    ↓
Database: 
  - SELECT FROM quizzes WHERE story_id = ?
  - SELECT FROM quiz_questions WHERE quiz_id = ?
  - Randomize question order, remove correct_option_id
    ↓
Response: {quiz_id, questions: [{question_id, text, options}], attempts_remaining}
    ↓
Client shows quiz to user, user answers
    ↓
Client POST /quiz/attempt {quiz_id, story_id, answers: [{question_id, chosen_option_id}], client_elapsed_seconds}
    ↓
Server validates:
  - Elapsed time ≥ 8 seconds (anti-bot)
  - Quiz exists, user has attempts remaining
  - All answer questions are in quiz
    ↓
Score calculation:
  - Count correct answers / total questions
  - passed = score ≥ 70%
    ↓
Fraud check:
  - Anti-repetition (same answer pattern as user's last 5 attempts?)
  - Temporal anomalies (too fast on similar questions?)
  - Insert log if flagged
    ↓
If passed:
  - base_credits = 10
  - if new_user (created_at < 7 days): base_credits *= 0.3
  - credits_earned_today += base_credits
  - if credits_earned_today > daily_cap: credits_awarded = daily_cap - (credits_earned_today - base_credits)
    ↓
Database:
  - INSERT INTO attempts {user_id, quiz_id, story_id, passed, score_percent, credits_awarded, elapsed_seconds}
  - INSERT INTO attempt_answers [...] (one per question)
  - INSERT INTO rewards_ledger {user_id, delta_credits, reason: 'quiz_pass', story_id}
    ↓
Response: {passed, score_percent, credits_awarded, balance_preview, attempts_remaining}
```

### 4. **Ingestion Pipeline Flow** (every 15 min)
```
Scheduler fires _run_collect()
    ↓
load_active_feeds(feed_registry_v1.csv) → 30 feeds
    ↓
For each feed:
  fetch_with_retry(url) → bytes
  parse_feed(bytes) → list[ParsedItem]
  validate_item(ParsedItem) → accept/reject
  INSERT feed_items_raw table
    ↓
[3031 items inserted in feed_items_raw]
    ↓
Scheduler fires _run_normalize()
    ↓
fetch_feed_items_raw() → rows with status='pending'
    ↓
For each raw item:
  clean_text(title, snippet)
  resolve_canonical_url(source_url) → canonical_url
  build_dedup_key(...) → check if duplicate
  IF unique:
    CREATE story record (story_id = deterministic_sha1)
    CREATE story_sources record
    UPDATE dedup_registry
  ELSE:
    SKIP (mark as duplicate)
    ↓
[stories table populated]
    ↓
Scheduler fires _run_keypoints()
    ↓
fetch_keypoint_candidates(db_path) → stories without keypoints
    ↓
For each story (max 150 per run):
  LLM_API(prompt=f"Extract 3-5 key points from: {headline}\n{summary}")
  parse_response() → list[str]
  INSERT story_key_points (5 rows per story)
  UPDATE stories.keypoints_generated_at
    ↓
Scheduler fires _run_quiz_pool()
    ↓
fetch_quiz_candidates(db_path) → stories without quizzes
    ↓
For each story:
  LLM_API(prompt=f"Generate 2-3 quiz questions for: {headline}...\nanswers must test comprehension")
  parse_questions() → list[{question, options: [a, b, c, d], correct: ?}]
  CREATE quiz record
  INSERT quiz_questions (3 rows per quiz, with correct_option_id hashed)
  UPDATE stories.quiz_status = 'quiz_available'
    ↓
Scheduler fires _run_analytics()
    ↓
Aggregates KPIs across all tables
    ↓
[Pipeline completes, next cycle in 15 minutes]
```

---

## 🎯 Component Interactions Matrix

| Component | Interacts With | Via | Purpose |
|-----------|----------------|-----|---------|
| **API (auth)** | User DB | SQL INSERT/SELECT | Register/login users |
| **API (feed_story)** | Stories DB | SQL SELECT | Fetch feed + story details |
| **API (quiz)** | Quizzes DB, Attempts DB | SQL SELECT/INSERT | Serve + score quizzes |
| **API (rewards)** | Rewards Ledger DB | SQL SELECT/INSERT | Track user balance |
| **Scheduler** | Collector modules | Python import | Orchestrate pipeline |
| **Collector** | RSS feeds | HTTP GET | Fetch articles |
| **Collector** | Feed Registry CSV | File read | Load feed list |
| **Normalizer** | Canonical URL module | Python function | Resolve redirects |
| **LLM Generators** | Ollama/OpenAI | HTTP POST | Generate keypoints/quizzes |
| **LLM Generators** | Stories DB | SQL SELECT/UPDATE | Read/write enrichment |
| **All modules** | Config module | Python import | Read environment settings |

---

## 📊 Maturity Assessment

### Overall: **ALPHA (40% Production Readiness)**

#### Completed & Solid (70-90% complete)
- ✅ **Core API routes** — FastAPI server, CORS, routing
- ✅ **Authentication** — Magic link + JWT working
- ✅ **Story feed** — Topic-based pagination working
- ✅ **Quiz scoring** — Basic quiz engine + reward logic
- ✅ **Database schema** — Comprehensive, normalized
- ✅ **RSS collector** — Parsing, validation, error handling
- ✅ **Configuration** — Flexible env-based config
- ✅ **Unit tests** — Basic test coverage for core modules
- ✅ **Deduplication** — 24h window working

#### Partially Complete (40-60% complete)
- ⚠️ **Normalizer** — Core logic works but **not tested in production** (never executed successfully in batch)
- ⚠️ **Keypoints generator** — Functional but slow (25s/request), quality depends on LLM
- ⚠️ **Quiz generator** — Functional but needs prompt engineering
- ⚠️ **Fraud detection** — Basic pattern checks exist but not comprehensive
- ⚠️ **Analytics dashboard** — Stub endpoints, not implemented
- ⚠️ **Sessions** — Minimal implementation, no server-side revocation

#### Missing / Stubbed (0-20% complete)
- ❌ **Production database** — SQLite insufficient (no multi-writer, no replication)
- ❌ **Monitoring/alerting** — No logs to external service (e.g., Sentry, DataDog)
- ❌ **Rate limiting** — Slowapi included but not enforced on all routes
- ❌ **API versioning** — No v1/ prefix, breaking changes hard to manage
- ❌ **Async task queue** — Background jobs are polling-based, not event-driven
- ❌ **Caching** — No Redis/Memcached, all queries hit SQLite
- ❌ **Load testing** — No performance benchmarks
- ❌ **Deployment automation** — No Docker, Kubernetes, CI/CD pipeline
- ❌ **HTTPS/TLS** — Dev mode only, no certificate management
- ❌ **Blockchain integration** — Phase 2, not started

---

## 🚀 Critical Path to Production

### Immediate Blockers (Must Fix)
1. **Database Upgrade** — Replace SQLite with PostgreSQL
   - Reason: SQLite doesn't support concurrent writers, critical for API + scheduler
   - Effort: ~2 weeks (schema migration, connection pooling, transactions)

2. **Normalizer Debugging** — Fix batch processing (currently hangs/fails silently)
   - Reason: Cannot proceed without normalized story data
   - Effort: ~1 week (add logging, test with real data)

3. **LLM Integration Testing** — Benchmark latency & cost
   - Reason: 25s/story × 3000 stories = too slow, need caching/batching
   - Effort: ~1 week (profile, implement caching)

### High-Priority (Should Fix Before MVP)
4. **Fraud Detection** — Strengthen beyond pattern matching
   - Implement ML-based anomaly detection
   - Add rate limiting per IP/user_id
   - Implement CAPTCHA for suspicious attempts

5. **Monitoring & Alerting** — Add observability
   - Export logs to centralized service
   - Set up alerts for pipeline failures
   - Create dashboard for ops team

6. **E2E Testing** — Write integration tests
   - Test full pipeline: RSS → collector → normalizer → quiz → user attempt
   - Test fraud detection edge cases
   - Test API error scenarios

### Medium-Priority (Before Public Launch)
7. **API Versioning** — Add /v1/ prefix, document deprecation path
8. **Caching** — Implement Redis for frequently-accessed stories/quizzes
9. **Async Task Queue** — Replace polling with event-driven (Celery, RQ)
10. **Deployment** — Dockerize, add Docker Compose, Kubernetes manifests

---

## 🔧 Key Configuration Parameters

| Parameter | Default | Recommendation | Impact |
|-----------|---------|-----------------|--------|
| `COLLECTOR_INTERVAL_MINUTES` | 15 | 15 (dev), 60 (prod) | Ingestion frequency |
| `KEYPOINTS_TIMEOUT_SECONDS` | 25 | 30 (if using cloud LLM) | LLM timeout |
| `QUIZ_POOL_ENABLED` | True | Should always be True (runtime feature) | Quiz generation |
| `REQUEST_TIMEOUT_SECONDS` | 8 | 10 (RSS feeds can be slow) | HTTP timeout for feed fetching |
| `DEDUP_WINDOW_HOURS` | 24 | 24 (good default) | Deduplication window |
| `JWT_EXPIRE_DAYS` | 7 | 7 (mobile UX) | JWT token lifetime |
| `MAGIC_LINK_EXPIRE_MINUTES` | 15 | 15 (security) | Magic link validity |
| `API_PORT` | 8000 | 8000 | Server port |
| `LLM_PROVIDER` | ollama | openai (prod) | Keyset: "ollama" or "openai" |
| `OLLAMA_BASE_URL` | http://localhost:11434 | Remote Ollama instance | Ollama endpoint |

---

## 📝 Testing Status

### Unit Tests (Basic Coverage)
- ✅ `test_canonical_url.py` — URL normalization logic
- ✅ `test_dedup.py` — Deduplication key generation
- ✅ `test_keypoints_generator.py` — LLM prompt formatting (mock)
- ✅ `test_normalizer.py` — Text cleaning, parsing
- ✅ `test_quiz_pool_generator.py` — Question parsing (mock)
- ✅ `test_story_service.py` — Story retrieval logic

### Integration Tests (Missing)
- ❌ End-to-end pipeline test (E2E)
- ❌ API endpoint integration tests
- ❌ Database transaction isolation tests
- ❌ Fraud detection edge cases
- ❌ Quiz scoring with multiple LLM responses

### Load Tests (Missing)
- ❌ API under concurrent load
- ❌ Collector with large feed batches
- ❌ LLM latency under workload

---

## 🔐 Security Posture

| Aspect | Status | Notes |
|--------|--------|-------|
| **Authentication** | ✅ Basic | Magic link + JWT working, but no 2FA |
| **Authorization** | ✅ Basic | Route-level access control via `get_current_user` |
| **Password** | ✅ Passwordless | Magic links, no password storage (good!) |
| **Secrets** | ⚠️ Risky | JWT secret in `config.py`, no Key Vault integration |
| **HTTPS** | ❌ None | Dev mode only (localhost), no TLS in production |
| **CORS** | ⚠️ Too Permissive | Default `*` (all origins), should restrict to frontend domain |
| **Rate Limiting** | ⚠️ Configured but Not Enforced | Slowapi middleware included but not applied to all routes |
| **SQL Injection** | ✅ Protected | Using parameterized queries throughout |
| **Fraud Detection** | ⚠️ Minimal | Pattern matching only, no IP-based detection |
| **Logging** | ⚠️ Local only | Logs to files/stdout, no centralized logging |

---

## 📦 Dependencies

### Core Dependencies (from pyproject.toml)
```
fastapi>=0.111              # REST API framework
uvicorn[standard]>=0.30     # ASGI server
pydantic>=2.7               # Data validation
python-dotenv>=1.0          # Environment config
httpx>=0.27                 # HTTP client (async)
python-jose[cryptography]   # JWT handling
APScheduler>=3.10           # Background job scheduling
slowapi>=0.1.9              # Rate limiting
feedparser>=6.0             # RSS/Atom parsing
```

### Optional Dependencies
```
pytest>=8.0                 # Testing
pytest-asyncio>=0.23        # Async test support
```

### External Services
```
Ollama >= 0.1.0             # Local LLM (default)
OpenAI API                  # Cloud LLM alternative
Resend API                  # Email delivery (optional, dev uses stdout)
Google News RSS feeds       # Content source (30 feeds)
```

---

## 📋 Known Issues & Limitations

### Critical
1. **Normalizer not running** — Pipeline breaks after collector, stories table stays empty
   - Investigation needed: timeout? memory leak? SQL error?
   - Workaround: Run manually in terminal (works) but not in scheduled pipeline

2. **SQLite concurrency** — API + scheduler compete for write lock
   - Risk: Data corruption under load
   - Mitigation: Run API and scheduler in separate processes (current architecture)
   - Fix: Upgrade to PostgreSQL

### High Priority
3. **LLM latency** — 25s/request × 3000 stories = 1.25 hours minimum
   - Risk: Stale content
   - Mitigation: Batch requests, implement caching
   - Fix: Use async batch API (OpenAI) or distributed Ollama

4. **No monitoring** — Silent failures in background jobs
   - Risk: Data pipeline breaks without alerting
   - Fix: Add stderr/stdout to centralized logging service

5. **Magic link email** — Only logs to stdout in dev mode
   - Risk: Production mode requires Resend API key, not configured
   - Fix: Set `MAGIC_LINK_DELIVERY=resend` + `RESEND_API_KEY`

### Medium Priority
6. **No caching** — All quiz/feed reads hit SQLite on each request
   - Risk: Poor response time under load
   - Fix: Add Redis cache layer

7. **No CORS restriction** — Accepts requests from any origin
   - Risk: Unauthorized API usage
   - Fix: Set `CORS_ORIGINS` to frontend domain only

8. **JWT not revocable** — No server-side session invalidation
   - Risk: Can't immediately log out user (must wait for expiry)
   - Fix: Add session blacklist table + check on protected routes

---

## 📚 Repository Structure Summary

```
polinews/
├── __init__.py
├── config.py                          # Unified configuration
├── main.py                            # CLI entry points
├── api/                               # FastAPI REST endpoints
│   ├── __init__.py
│   ├── app.py                         # FastAPI app factory
│   ├── auth.py                        # Magic link + JWT routes
│   ├── feed_story.py                  # Story feed + detail routes
│   ├── quiz.py                        # Quiz serve + attempt routes
│   ├── rewards.py                     # Balance + comment routes
│   ├── dashboard.py                   # Personal stats (stub)
│   ├── sessions.py                    # Session mgmt (stub)
│   └── analytics.py                   # Publisher KPIs (stub)
├── auth/                              # Authentication utilities
│   ├── __init__.py
│   ├── jwt.py                         # JWT encoding/decoding
│   └── magic_link.py                  # Magic link token mgmt
├── collector/                         # RSS ingestion pipeline
│   ├── __init__.py
│   ├── rss_collector.py               # Fetch + parse RSS
│   ├── parser.py                      # XML parsing
│   ├── normalizer.py                  # Clean + deduplicate
│   ├── dedup.py                       # Dedup logic
│   ├── canonical_url.py               # URL canonicalization
│   ├── keypoints_generator.py         # LLM summarization
│   ├── quiz_pool_generator.py         # LLM quiz generation
│   ├── db.py                          # Collector DB helpers
│   ├── config.py                      # Collector config
│   ├── collector_logging.py           # Structured logging
│   └── README.md                      # Pipeline documentation
├── db/                                # Database layer
│   ├── __init__.py
│   ├── connection.py                  # Connection factory
│   └── schema.py                      # SQLite schema
└── worker/                            # Background jobs
    ├── __init__.py
    ├── scheduler.py                   # APScheduler orchestration
    └── analytics_job.py               # KPI computation
```

---

## 🎓 Code Quality & Practices

### Good Practices ✅
- Consistent code style (black-formatted)
- Comprehensive docstrings on public functions
- Type hints throughout (Python 3.11+)
- Environment-based configuration
- Password-less auth (no password storage)
- Parameterized SQL queries (SQL injection safe)
- Modular design (each component has clear responsibility)
- Error handling with logging
- CSV-based configuration for feeds (not hardcoded)

### Areas for Improvement ⚠️
- Limited async/await (mostly blocking calls)
- No dataclass/namedtuple for complex types (dict used instead)
- Limited use of composition (some functions too monolithic)
- No dependency injection (tight coupling to DB paths)
- Limited error context (exception messages could be more descriptive)
- No request ID tracing across services
- Limited docstring examples (show usage!)

---

## 🏁 Summary Table

| Aspect | Status | Coverage | Risk |
|--------|--------|----------|------|
| **Core API** | ✅ Functional | 7 routers | Low |
| **Authentication** | ✅ Functional | Magic link + JWT | Low |
| **Database Schema** | ✅ Comprehensive | 13 tables + indexes | Low |
| **Collector** | ⚠️ Partial | 4/5 stages working | Medium |
| **Normalizer** | ❌ Broken (undebugged) | Should work, not tested | High |
| **LLM Integration** | ✅ Functional | Keypoints + Quiz | Medium (slow) |
| **Unit Tests** | ⚠️ Basic | 6 test files | Medium |
| **Production Readiness** | ❌ Not Ready | 40% ready | High |
| **Monitoring** | ❌ None | 0% | High |
| **Deployment** | ⚠️ Manual | No automation | High |

---

## 📞 Next Steps for Development

1. **Immediate (This Week):**
   - Debug normalizer (add verbose logging, test with small dataset)
   - Set up monitoring (e.g., Sentry for error tracking)
   - Run end-to-end test of full pipeline

2. **Short-term (1-2 Weeks):**
   - Migrate SQLite → PostgreSQL
   - Implement caching (Redis) for quizzes/stories
   - Improve fraud detection (IP-based + ML)

3. **Medium-term (1 Month):**
   - Add comprehensive integration tests
   - Implement async batch processing for LLM calls
   - Deploy on staging environment (Docker + k8s)

4. **Long-term (2+ Months):**
   - On-chain integration (Phase 2 blockchain)
   - Publisher dashboard improvements
   - Advanced analytics & reporting

---

**Document Version:** 1.0  
**Last Reviewed:** 2026-03-19  
**Maintainer:** Development Team
