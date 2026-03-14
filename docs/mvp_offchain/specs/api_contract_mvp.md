# api_contract_mvp

## Content API

### `GET /feed?topic=&page=`
- Returns paginated stories by topic.
- Query params:
  - `topic` (required)
  - `page` (optional, default 1)
  - `limit` (optional, default 20)
- 200 response fields:
  - `items[]`: `story_id`, `headline`, `snippet`, `topic`, `published_at`, `source_count`
  - `page`, `limit`, `has_next`

### `GET /stories/:story_id`
- Returns story page payload.
- 200 response fields:
  - `story_id`, `topic_slug`, `headline`, `summary`, `key_points[]`, `sources[]`, `published_at`
  - `quiz_available`, `comment_enabled`
- Availability rules:
  - `quiz_available=true` only if runtime quiz for the story is available.
  - `comment_enabled` remains independent from quiz availability.
- Errors:
  - `404` story not found
  - `410` story exists but is not publishable (or fails runtime minimum checks)

### `GET /stories/:story_id/page`
- Returns rendered HTML story page in fixed template order:
  - topic badge, headline, snippet, key points, attribution block, verification box, credits teaser.
- Query params:
  - `auth` (`0`/`1`, optional) to preview logged-out/logged-in credits teaser in staging.
  - `balance` (optional integer, default `30`) used when `auth=1`.
- Errors:
  - `404` story not found
  - `410` story not publishable/runtime invalid

## Verification and rewards API

### `GET /quiz?story_id=`
- 200:
  - `quiz_id`, `story_id`, `questions[]`, `attempts_remaining`, `cooldown_seconds`.
  - `questions[]`: `question_id`, `text`, `options[]`.
  - `options[]`: `option_id`, `text`.
- Errors: 404, 409, 429.

### `POST /attempt`
- Request: `quiz_id`, `story_id`, `answers[]`, `client_elapsed_seconds`.
- 200: `passed`, `score`, `credits_awarded`, `balance_preview`, `cooldown_seconds`.
- Errors: 400, 403, 404, 409, 429.

### `POST /comment`
- Request: `story_id`, `text`.
- 200: `accepted`, `review_status`, `credits_provisional`.
- Errors: 400, 409, 429.

### `GET /balance`
- 200: `current_balance`, `pending_balance`, `recent_transactions[]`.

### `POST /redeem`
- Request: `reward_id`, `idempotency_key`.
- 200: `redeem_status`, `credits_spent`, `remaining_balance`.
- Errors: 400, 402, 409, 429.

## Publisher dashboard API

### `GET /publisher-dashboard`
- 200:
  - `funnel`: `box_viewed`, `quiz_started`, `quiz_passed`
  - `quality`: `avg_quiz_time`, `comment_accept_rate`
  - `economics`: `credits_issued`, `credits_revoked`, `verified_read_cost`
  - `fraud`: `signals_open`, `signals_high_severity`

## Analytics API (v0.2)

### `GET /analytics/story/:story_id`
- 200:
  - `comprehension_score`, `engagement_score`, `reading_time_p50`, `difficulty_index`
- Auth: publisher API key.

### `GET /analytics/topic/:topic_slug?locale=&from=&to=`
- 200:
  - weekly `attempt_rate`, `comprehension_score`, `avg_read_seconds`, `unique_readers`
- Auth: publisher or researcher API key.

### `GET /analytics/publisher/benchmark`
- 200:
  - publisher metrics vs platform median by topic and locale.
- Auth: publisher API key.

### `GET /analytics/export?format=parquet&from=&to=`
- 200:
  - signed URL or streamed dataset export.
- Auth: licensed researcher API key.

## Phase 2 Voucher API (readiness)

### `POST /voucher/issue`
- Request: `user_id`, `user_address`, `story_id`, `amount_poli`.
- 200: `voucher_payload`, `server_signature`, `expiry`, `nonce`.
- Auth: internal service key.

### `GET /voucher/status/:nonce`
- 200: `status` (`issued` | `claimed` | `expired`), `claimed_tx_hash`.
- Auth: internal service key.

## Compliance API

### `DELETE /user/data`
- Purpose: GDPR deletion request for reading history and export-ready derived data.
- 202: accepted with async job id.
- Auth: user session token.
