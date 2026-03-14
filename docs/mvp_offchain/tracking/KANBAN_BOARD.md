# Kanban Board - MVP Off-Chain

Regola dipendenze richiesta: `Dipende da` indica solo chi deve agire (`ME/Codex` oppure `TU/Founder`).

## Snapshot
- Total cards: 65
- Backlog: 46
- In progress: 0
- Blocked: 2
- Done: 17

## Backlog
- **W2-03** - Implement story rendering | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D9 | Depends on IDs: `W2-01`
- **W2-04** - Define quiz format | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D9 | Depends on IDs: `W2-01`
- **W2-05** - Implement quiz pool generation | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D10 | Depends on IDs: `W2-04`
- **W2-06** - Implement GET /quiz | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D10 | Depends on IDs: `W2-05`
- **W2-07** - Implement POST /attempt | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D11 | Depends on IDs: `W2-06`
- **W2-08** - Implement POST /comment | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D11 | Depends on IDs: `W2-03`
- **W2-09** - Implement rewards ledger | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D12 | Depends on IDs: `W2-07+W2-08`
- **W2-10** - Implement GET /balance | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D12 | Depends on IDs: `W2-09`
- **W2-11** - Define reward policy | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D12 | Depends on IDs: `W2-09`
- **W2-12** - Implement light auth | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D13 | Depends on IDs: `W2-03`
- **W2-13** - Week 2 checkpoint | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D14 | Depends on IDs: `W2-01..W2-12`
- **W2-14** - Extend SQL schema for data revenue layer | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D14 | Depends on IDs: `W1-09`
- **W2-15** - Add quiz question task types and campaign fields | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D14 | Depends on IDs: `W2-04`
- **W2-16** - Define pseudonymization and DPA export policy | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D14 | Depends on IDs: `W2-14`
- **W2-17** - Extend API contract with analytics and voucher endpoints | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D14 | Depends on IDs: `W2-10`
- **W3-01** - Implement rate limits | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D15 | Depends on IDs: `W2-13`
- **W3-02** - Implement attempt caps and cooldown | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D15 | Depends on IDs: `W2-07`
- **W3-03** - Enforce one reward per story/account | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D16 | Depends on IDs: `W2-09`
- **W3-04** - Implement new user multiplier | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D16 | Depends on IDs: `W2-11`
- **W3-05** - Implement fraud signals | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D17 | Depends on IDs: `W3-01`
- **W3-06** - Define fraud review SOP | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D17 | Depends on IDs: `W3-05`
- **W3-07** - Implement reward revoke | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D18 | Depends on IDs: `W3-06`
- **W3-08** - Implement redemption catalog | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D18 | Depends on IDs: `W2-10`
- **W3-09** - Implement POST /redeem idempotent | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D19 | Depends on IDs: `W3-08`
- **W3-10** - Implement publisher dashboard | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D19 | Depends on IDs: `W2-09+W3-05`
- **W3-11** - Freeze KPI formula and thresholds | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D20 | Depends on IDs: `W3-10`
- **W3-12** - Week 3 checkpoint | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D21 | Depends on IDs: `W3-01..W3-11`
- **W3-13** - Implement reading sessions capture | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D21 | Depends on IDs: `W2-14`
- **W3-14** - Implement comprehension events and qa pair writes | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D21 | Depends on IDs: `W2-14`
- **W3-15** - Implement annotation task model and injection rules | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D21 | Depends on IDs: `W2-15`
- **W3-16** - Build dataset export sample parquet | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D21 | Depends on IDs: `W3-14`
- **W4-01** - Run 20 e2e scenarios | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D22 | Depends on IDs: `W3-12`
- **W4-02** - Run load test | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D23 | Depends on IDs: `W3-12`
- **W4-03** - Run 7 antifraud simulations | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D23 | Depends on IDs: `W3-06`
- **W4-04** - Harden observability | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D24 | Depends on IDs: `W4-02`
- **W4-05** - Define incident runbook | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D24 | Depends on IDs: `W4-04`
- **W4-06** - Soft launch at 10-20 percent | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D25 | Depends on IDs: `W4-01`
- **W4-07** - Full pilot run | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D26-D27 | Depends on IDs: `W4-06`
- **W4-08** - Compute final KPIs and evaluate gates | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D28 | Depends on IDs: `W4-07`
- **W4-09** - Postmortem and backlog v2 | Owner: Founder | Priority: P1 | Dipende da: TU (Founder) | Target: D28 | Depends on IDs: `W4-08`
- **W4-10** - Formal closeout | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D28 | Depends on IDs: `W4-08`
- **W4-11** - Add data monetization KPIs and alerts | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D28 | Depends on IDs: `W3-16`
- **W4-12** - Prepare AI buyer integration pack | Owner: Founder | Priority: P1 | Dipende da: TU (Founder) | Target: D28 | Depends on IDs: `W3-16`
- **W4-13** - Define phase2 blockchain contracts and voucher flow | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D28 | Depends on IDs: `W2-17`
- **W4-14** - Finalize GDPR and MiCA readiness checklist | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D28 | Depends on IDs: `W2-16`
- **W4-15** - Week4 v0.2 decision checkpoint | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D28 | Depends on IDs: `W4-08+W4-11+W4-14`

## In progress
- (none)

## Blocked
- **G-02** - Create 28-day calendar | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D1 | Depends on IDs: `G-01`
- **W2-02** - Implement key-point generation | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D9 | Depends on IDs: `W2-01`

## Done
- **G-01** - Create board with 4 columns | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D1 | Depends on IDs: `-`
- **G-03** - Define SLA | Owner: Founder | Priority: P1 | Dipende da: TU (Founder) | Target: D1 | Depends on IDs: `G-01`
- **G-04** - Define env naming | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D1 | Depends on IDs: `G-01`
- **G-05** - Define issue templates | Owner: Founder | Priority: P1 | Dipende da: TU (Founder) | Target: D1 | Depends on IDs: `G-01`
- **W1-01** - Freeze topics taxonomy | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D2 | Depends on IDs: `G-01`
- **W1-02** - Build feed registry | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D2 | Depends on IDs: `W1-01`
- **W1-03** - Define ingestion policy | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D2 | Depends on IDs: `W1-02`
- **W1-04** - Implement RSS collector | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D3 | Depends on IDs: `W1-02`
- **W1-05** - Implement normalization | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D3 | Depends on IDs: `W1-04`
- **W1-06** - Implement canonical URL resolver | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D4 | Depends on IDs: `W1-05`
- **W1-07** - Implement dedup | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D4 | Depends on IDs: `W1-05`
- **W1-08** - Define source quality rules | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D4 | Depends on IDs: `W1-02`
- **W1-09** - Create ingestion data model | Owner: Freelance | Priority: P0 | Dipende da: ME (Codex) | Target: D5 | Depends on IDs: `W1-05`
- **W1-10** - Define stale fallback | Owner: Freelance | Priority: P1 | Dipende da: ME (Codex) | Target: D5 | Depends on IDs: `W1-03`
- **W1-11** - Define attribution legal policy | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D5 | Depends on IDs: `W1-08`
- **W1-12** - Week 1 checkpoint | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D7 | Depends on IDs: `W1-01..W1-11`
- **W2-01** - Define story template | Owner: Founder | Priority: P0 | Dipende da: TU (Founder) | Target: D8 | Depends on IDs: `W1-12`

