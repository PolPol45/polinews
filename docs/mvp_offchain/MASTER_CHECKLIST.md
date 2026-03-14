# Master Checklist - MVP Off-Chain Poli-News (Google News RSS)

Version: v1.1 (business alignment)  
Date: 2026-03-14  
Scope lock: Off-chain MVP plus phase2 readiness, Google News RSS global multi-topic, title+snippet+source links, quiz/comment verification on Poli-News story pages.

## 0) v0.2 Business Alignment

- Primary monetization remains publisher subscription during the 4-week MVP.
- Future process is aligned to add:
  - AI training data licensing.
  - Human annotation task sales (RLHF data).
  - Verified attention analytics premium.
  - Phase2 on-chain voucher flow for `$POLI`.
- Current implementation work completed in Week 1 must stay reusable for all four revenue streams.
- Source of truth for current status and sequencing is `tracking/master_tasks.csv` and `tracking/KANBAN_BOARD.md`.

## 1) Success gates (must pass)

- [ ] Gate A - Usability: attempt rate 15-25% and pass rate 60-80% over pilot window.
- [ ] Gate B - Sustainability: verified read cost stays under threshold agreed at kickoff.
- [ ] Gate C - Risk: fraud queue remains operationally manageable (no unresolved critical spikes >24h).

## 2) Non-negotiable constraints

- [ ] No wallet.
- [ ] No KYC/AML.
- [ ] No on-chain transactions.
- [ ] No full-text copy from sources.
- [ ] Every story page shows source attribution and outbound links.

## 3) Task register (execution truth source)

Status values: `NOT_STARTED`, `IN_PROGRESS`, `BLOCKED`, `DONE`.

Single source of truth:
- `docs/mvp_offchain/tracking/master_tasks.csv`
- `docs/mvp_offchain/tracking/KANBAN_BOARD.md`
- `docs/mvp_offchain/tracking/checkpoints.md`

v0.2 extension cards are now included in the same task stream:
- Week 2 additions: `W2-14..W2-17` (data schema extension, compliance policy, API extension).
- Week 3 additions: `W3-13..W3-16` (behavioral capture, annotation pipeline, dataset export sample).
- Week 4 additions: `W4-11..W4-15` (data monetization KPIs, buyer pack, phase2 and compliance readiness, final v0.2 gate).

Current status snapshot is generated from `master_tasks.csv` and reflected in `KANBAN_BOARD.md`.

## 4) Daily control routine (fixed)

| Time | Task | Owner | Pass condition |
|---|---|---|---|
| 09:00 | Check ingestion lag + feed errors | Founder | No critical ingestion error unresolved >2h |
| 11:00 | Check funnel KPI drift | Founder | Deviations logged and assigned |
| 14:00 | Review fraud queue | Founder | High severity signals triaged same day |
| 17:00 | Check redemption and daily reward cost | Founder | Daily budget cap not breached |
| 19:00 | Write 10-line daily report | Founder | Report saved in tracking folder |

## 5) Critical evidence pack (must exist by Day 28)

- [ ] `topics_v1`
- [ ] `feed_registry_v1`
- [ ] `ingestion_policy_v1`
- [ ] `source_policy_v1`
- [ ] `story_template_v1`
- [ ] `quiz_spec_v1`
- [ ] `reward_policy_v1`
- [ ] `kpi_spec_v1`
- [ ] API test report
- [ ] Load/perf report
- [ ] Fraud simulation log
- [ ] Decision memo with `GO | CONDITIONAL_GO | NO_GO`

## 6) Stop conditions (automatic)

- [ ] Pause rewards if abnormal fraud spike exceeds operational threshold.
- [ ] Pause new traffic if ingestion fails for more than defined stale window.
- [ ] Pause redemption if ledger consistency check fails.

## 7) Final sign-off checklist

- [ ] Product flow is end-to-end functional.
- [ ] Off-chain ledger is auditable and reversible.
- [ ] Attribution policy is respected on every story page.
- [ ] KPI dashboard updates within agreed SLA.
- [ ] Incident and fraud runbooks are executable by founder alone.
- [ ] Decision memo is approved and archived.
