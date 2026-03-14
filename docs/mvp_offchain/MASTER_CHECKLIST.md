# Master Checklist - MVP Off-Chain Poli-News (Google News RSS)

Version: v1.0  
Date: 2026-03-05  
Scope lock: Off-chain only, Google News RSS, global multi-topic, title+snippet+source links, quiz/comment on Poli-News story pages.

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

| ID | Week | Task | Owner | Priority | Depends on | Est. h | Target day | Status | DoD | Evidence |
|---|---|---|---|---|---|---:|---|---|---|---|
| G-01 | 0 | Create board with Backlog/In progress/Blocked/Done | Founder | P0 | - | 1 | D1 | NOT_STARTED | Board contains all IDs from this file | Screenshot in `/docs/mvp_offchain/tracking/checkpoints.md` |
| G-02 | 0 | Create 28-day calendar with review every 2 days | Founder | P0 | G-01 | 1 | D1 | NOT_STARTED | Calendar shared and linked in tracker | Link in checkpoints |
| G-03 | 0 | Define MVP SLA (critical <24h, high <48h) | Founder | P1 | G-01 | 1 | D1 | NOT_STARTED | SLA file approved | `/docs/mvp_offchain/governance/sla_mvp.md` |
| G-04 | 0 | Define env naming `dev/staging/pilot` | Freelance | P1 | G-01 | 0.5 | D1 | NOT_STARTED | Naming used in docs and logs | `/docs/mvp_offchain/governance/env_naming.md` |
| G-05 | 0 | Define issue templates (bug, feature, fraud, ops) | Founder | P1 | G-01 | 1 | D1 | NOT_STARTED | 4 templates available | `/docs/mvp_offchain/governance/issue_templates.md` |
| W1-01 | 1 | Freeze global topic taxonomy (8-12) | Founder | P0 | G-01 | 1 | D2 | NOT_STARTED | Topics list with stable slugs | `/docs/mvp_offchain/specs/topics_v1.md` |
| W1-02 | 1 | Create Google News RSS feed registry per topic/locale | Freelance | P0 | W1-01 | 2 | D2 | NOT_STARTED | Registry has URL + topic + locale + status | `/docs/mvp_offchain/specs/feed_registry_v1.csv` |
| W1-03 | 1 | Define ingestion refresh/retry policy | Freelance | P0 | W1-02 | 1 | D2 | NOT_STARTED | Policy includes refresh, retry, timeout, stale mode | `/docs/mvp_offchain/specs/ingestion_policy_v1.md` |
| W1-04 | 1 | Implement RSS collector (fetch/parse/validate) | Freelance | P0 | W1-02 | 8 | D3 | NOT_STARTED | Raw items persisted with ingest timestamp | Service logs + DB sample |
| W1-05 | 1 | Implement normalization (`title/snippet/source/date/url`) | Freelance | P0 | W1-04 | 6 | D3 | NOT_STARTED | Required fields non-null for accepted records | Unit test report |
| W1-06 | 1 | Implement canonical URL resolver (base) | Freelance | P1 | W1-05 | 4 | D4 | NOT_STARTED | Canonical URL resolved on >=90% sample | QA sample report |
| W1-07 | 1 | Implement dedup (hash + source + time window + canonical URL) | Freelance | P0 | W1-05 | 6 | D4 | NOT_STARTED | Duplicate suppression active without high false positives | Dedup report |
| W1-08 | 1 | Define source quality rules (allow/deny/min reputation) | Founder | P0 | W1-02 | 1 | D4 | NOT_STARTED | Rules documented and ready for pipeline | `/docs/mvp_offchain/specs/source_policy_v1.md` |
| W1-09 | 1 | Create data model `feed_items_raw/stories/story_sources` | Freelance | P0 | W1-05 | 4 | D5 | NOT_STARTED | Tables and constraints created and validated | `/docs/mvp_offchain/specs/data_model_mvp.sql` |
| W1-10 | 1 | Define feed failure fallback (stale mode + alert) | Freelance | P1 | W1-03 | 2 | D5 | NOT_STARTED | System serves stale feed and raises alert | Chaos test note |
| W1-11 | 1 | Define attribution legal policy | Founder | P0 | W1-08 | 1 | D5 | NOT_STARTED | Attribution checklist approved | `/docs/mvp_offchain/specs/attribution_policy_v1.md` |
| W1-12 | 1 | Week 1 checkpoint | Founder | P0 | W1-01..W1-11 | 1 | D7 | NOT_STARTED | Ingestion stable, dedup active, schema validated | Checkpoint entry |
| W2-01 | 2 | Define Poli-News story format (`headline/snippet/key points/sources`) | Founder | P0 | W1-12 | 1 | D8 | NOT_STARTED | Template approved | `/docs/mvp_offchain/specs/story_template_v1.md` |
| W2-02 | 2 | Implement key-point generation (rule based) | Freelance | P0 | W2-01 | 8 | D9 | NOT_STARTED | 3-5 key points per eligible story | QA on 50 stories |
| W2-03 | 2 | Implement story page rendering with full attribution | Freelance | P0 | W2-01 | 6 | D9 | NOT_STARTED | Public page shows source links and disclaimer | Staging URLs |
| W2-04 | 2 | Define quiz format (2-3 questions) | Founder | P0 | W2-01 | 1 | D9 | NOT_STARTED | Quiz format and scoring rules documented | `/docs/mvp_offchain/specs/quiz_spec_v1.md` |
| W2-05 | 2 | Implement quiz pool generation per story | Freelance | P0 | W2-04 | 10 | D10 | NOT_STARTED | Pool available for >=80% stories | Coverage report |
| W2-06 | 2 | Implement `GET /quiz?story_id=` | Freelance | P0 | W2-05 | 4 | D10 | NOT_STARTED | Returns random quiz + attempts remaining | API tests |
| W2-07 | 2 | Implement `POST /attempt` scoring + elapsed time | Freelance | P0 | W2-06 | 6 | D11 | NOT_STARTED | Returns pass/score/credits/cooldown | API tests |
| W2-08 | 2 | Implement `POST /comment` anti-spam base | Freelance | P0 | W2-03 | 5 | D11 | NOT_STARTED | Valid comments accepted, spam rejected | Test cases |
| W2-09 | 2 | Implement off-chain rewards ledger | Freelance | P0 | W2-07,W2-08 | 6 | D12 | NOT_STARTED | Append-only credit/debit/revoke with reason | DB sample rows |
| W2-10 | 2 | Implement `GET /balance` | Freelance | P0 | W2-09 | 3 | D12 | NOT_STARTED | Current + pending balance + last transactions | API tests |
| W2-11 | 2 | Define reward policy (`base/bonus/cap/new_user_multiplier`) | Founder | P0 | W2-09 | 1 | D12 | NOT_STARTED | Policy versioned and referenced in backend | `/docs/mvp_offchain/specs/reward_policy_v1.md` |
| W2-12 | 2 | Implement light auth (magic link or social) | Freelance | P1 | W2-03 | 8 | D13 | NOT_STARTED | Stable login/session in staging | Auth QA |
| W2-13 | 2 | Week 2 checkpoint | Founder | P0 | W2-01..W2-12 | 1 | D14 | NOT_STARTED | End-to-end quiz to credits works | Demo note |
| W3-01 | 3 | Implement rate limits (account/IP/device) | Freelance | P0 | W2-13 | 6 | D15 | NOT_STARTED | Rate limits active on quiz/comment/redeem | Load test |
| W3-02 | 3 | Enforce attempts/day + cooldown per story | Freelance | P0 | W2-07 | 4 | D15 | NOT_STARTED | Violations blocked and logged | API tests |
| W3-03 | 3 | Enforce one reward per story/account | Freelance | P0 | W2-09 | 3 | D16 | NOT_STARTED | Double credit impossible | Conflict test |
| W3-04 | 3 | Implement user reputation and 7-day multiplier | Freelance | P1 | W2-11 | 4 | D16 | NOT_STARTED | New users get reduced reward by policy | Scenario QA |
| W3-05 | 3 | Implement `fraud_signals` table + reason codes | Freelance | P0 | W3-01 | 4 | D17 | NOT_STARTED | Anomalies create signals with severity/state | DB sample |
| W3-06 | 3 | Define fraud review queue SOP | Founder | P0 | W3-05 | 1 | D17 | NOT_STARTED | Manual review process documented | `/docs/mvp_offchain/runbooks/antifraud_review_runbook_v1.md` |
| W3-07 | 3 | Implement reward revoke with audit reason | Freelance | P0 | W3-06 | 4 | D18 | NOT_STARTED | Revocation updates balance and ledger | Revocation tests |
| W3-08 | 3 | Implement redemption catalog (discount + 24h premium) | Freelance | P0 | W2-10 | 5 | D18 | NOT_STARTED | 2 redeem options live with caps | UI/API tests |
| W3-09 | 3 | Implement `POST /redeem` idempotent | Freelance | P0 | W3-08 | 4 | D19 | NOT_STARTED | Duplicate requests do not double spend | API tests |
| W3-10 | 3 | Implement `GET /publisher-dashboard` | Freelance | P0 | W2-09,W3-05 | 6 | D19 | NOT_STARTED | KPI view with conversion/cost/fraud | Dashboard screenshots |
| W3-11 | 3 | Freeze KPI formulas and thresholds | Founder | P0 | W3-10 | 1 | D20 | NOT_STARTED | KPI spec final and signed | `/docs/mvp_offchain/specs/kpi_spec_v1.md` |
| W3-12 | 3 | Week 3 checkpoint | Founder | P0 | W3-01..W3-11 | 1 | D21 | NOT_STARTED | Dashboard, antifraud, redeem active | Checkpoint entry |
| W4-01 | 4 | Run 20 end-to-end critical scenarios | Founder | P0 | W3-12 | 4 | D22 | NOT_STARTED | 0 open blockers before full pilot | Test report |
| W4-02 | 4 | Run load test on ingestion + quiz APIs | Freelance | P0 | W3-12 | 4 | D23 | NOT_STARTED | Throughput and latency within limits | Perf report |
| W4-03 | 4 | Run antifraud simulations (7 abuse patterns) | Founder | P0 | W3-06 | 3 | D23 | NOT_STARTED | Signals and mitigations verified | Fraud log |
| W4-04 | 4 | Harden observability (errors/latency/lag/job failures) | Freelance | P1 | W4-02 | 4 | D24 | NOT_STARTED | Alerts and dashboards active | Ops screenshots |
| W4-05 | 4 | Define incident response runbook | Founder | P0 | W4-04 | 1 | D24 | NOT_STARTED | Runbook with owner/actions/SLA | `/docs/mvp_offchain/runbooks/ops_runbook_v1.md` |
| W4-06 | 4 | Soft launch at 10-20% traffic | Founder | P0 | W4-01 | 2 | D25 | NOT_STARTED | 48h stable KPI and errors | Pilot log |
| W4-07 | 4 | Full pilot run | Founder | P0 | W4-06 | 6 | D26-D27 | NOT_STARTED | Stable run with daily reporting | Daily reports |
| W4-08 | 4 | Compute final KPI and evaluate Gates A/B/C | Founder | P0 | W4-07 | 2 | D28 | NOT_STARTED | Decision memo produced | `/docs/mvp_offchain/tracking/decision_memo.md` |
| W4-09 | 4 | Postmortem + v2 backlog top 10 | Founder | P1 | W4-08 | 2 | D28 | NOT_STARTED | Prioritized backlog produced | `/docs/mvp_offchain/tracking/backlog_v2.md` |
| W4-10 | 4 | Formal MVP closeout | Founder | P0 | W4-08 | 1 | D28 | NOT_STARTED | All mandatory checklists signed | Closeout section in checkpoints |

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
