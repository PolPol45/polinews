# ingestion_policy_v1

## Schedule
- Refresh every 15 minutes.
- Jitter +/- 60 seconds to avoid burst calls.

## Networking controls
- Request timeout: 8 seconds.
- Max retries: 3 per feed run.
- Backoff: 1s, 3s, 9s.
- User agent: fixed and explicit `PoliNewsMVPFeedCollector/1.0`.

## Acceptance checks per item
- Must have title.
- Must have link.
- Must have source name or parsable domain.
- Published date fallback to ingestion timestamp when missing.

## Stale mode
- Enter stale mode if feed fetch fails for 3 consecutive runs.
- In stale mode, continue serving latest successful story snapshots.
- Raise alert on stale mode start and stale mode end.

## Logging requirements
- Log one line per feed run: `feed_id`, start/end, fetched count, accepted count, rejected count, error class.
- Log one line per item reject with reason code.
