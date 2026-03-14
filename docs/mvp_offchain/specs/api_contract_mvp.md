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
  - `story_id`, `headline`, `snippet`, `key_points[]`, `sources[]`
  - `quiz_available`, `comment_enabled`

## Verification and rewards API

### `GET /quiz?story_id=`
- 200: `quiz_id`, `questions[]`, `attempts_remaining`, `cooldown_seconds`.
- Errors: 404, 429.

### `POST /attempt`
- Request: `quiz_id`, `story_id`, `answers[]`, `client_elapsed_seconds`.
- 200: `passed`, `score`, `credits_awarded`, `balance_preview`, `cooldown_seconds`.
- Errors: 400, 403, 409, 429.

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
