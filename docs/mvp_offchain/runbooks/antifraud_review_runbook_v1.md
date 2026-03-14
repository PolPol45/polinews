# antifraud_review_runbook_v1

## Objective
Process fraud signals daily with predictable SLA and auditable actions.

## Inputs
- `fraud_signals` table
- Attempt logs
- Ledger history

## Review cadence
- Daily at 14:00.
- Emergency review within 2h for critical spikes.

## Severity mapping
- High: likely automated abuse or budget risk.
- Medium: suspicious pattern, needs confirmation.
- Low: weak signal, monitor only.

## Daily workflow
1. Pull open signals sorted by severity and recency.
2. Triage top high severity items first.
3. For each signal, gather user attempts + ledger entries + IP/device context.
4. Apply decision: `dismiss`, `watch`, `restrict`, `revoke`.
5. Record reason code and operator notes.
6. Verify balance consistency after revoke.
7. Update daily report with counts and outcomes.

## Allowed reason codes
- `too_fast_attempts`
- `duplicate_pattern`
- `multi_account_cluster`
- `cooldown_bypass`
- `redeem_spike`

## Escalation triggers
- >5 high severity signals within 60 min.
- Fraud flag rate exceeds defined threshold for 2 consecutive checks.
- Any ledger inconsistency during revoke.

## Outputs
- Updated signal statuses.
- Revoke audit trail.
- Daily fraud summary in report.
