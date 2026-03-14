# ops_runbook_v1

## Incidents covered
- Feed ingestion outage.
- API partial outage.
- Quiz/redeem failures.
- Fraud spikes.
- Ledger consistency alerts.

## Triage matrix
| Incident type | First action | Owner | SLA |
|---|---|---|---|
| Feed down | Enter stale mode, check retries | Founder | 1h |
| API errors > threshold | Throttle traffic, inspect logs | Freelance | 1h |
| Quiz failures | Disable quiz box temporarily | Freelance | 2h |
| Redeem anomalies | Pause redeem endpoint | Founder | immediate |
| Ledger mismatch | Freeze rewards and investigate | Founder + Freelance | immediate |

## Playbooks

### Feed down
1. Confirm if issue is single feed or global.
2. Activate stale mode if not active.
3. Disable failing feeds from registry if needed.
4. Post status in checkpoint log.

### API degradation
1. Identify failing endpoint.
2. Check recent deploy/config changes.
3. Roll back latest risky change if available.
4. Re-test critical path: story -> quiz -> attempt -> balance.

### Fraud spike
1. Increase rate limit strictness.
2. Enforce temporary reward cap if needed.
3. Process high severity queue first.
4. Consider temporary pause of redemption.

### Ledger inconsistency
1. Stop new reward writes.
2. Snapshot ledger and balances.
3. Run consistency queries.
4. Restore writes only after mismatch resolved.

## Exit criteria
- Core endpoint success rate recovered.
- No unresolved critical alerts.
- Post-incident actions logged with owner and deadline.
