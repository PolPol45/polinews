# MVP Off-Chain Package

This folder contains the operational implementation pack for the 4-week off-chain MVP.

## Files
- `MASTER_CHECKLIST.md`: master execution list with dependencies, DoD, and evidence.
- `governance/`: board, calendar, SLA, env naming, issue templates.
- `specs/`: topics, feed registry, ingestion/source/attribution policies, story/quiz/reward/KPI specs, API contract, SQL schema.
- `runbooks/`: antifraud and incident operations.
- `tracking/`: task CSV, checkpoints log, daily report template, decision memo, backlog v2.

## Day-1 quick start
1. Create board from `MASTER_CHECKLIST.md` and `tracking/master_tasks.csv`.
2. Fill checkpoint owner names and due days.
3. Confirm feed URLs in `specs/feed_registry_v1.csv` from your runtime environment.
4. Start tasks `G-01` to `G-05`.

## Control rule
Source of truth for status and sign-off:
- `tracking/master_tasks.csv`
- `tracking/KANBAN_BOARD.md`
- `tracking/checkpoints.md`

## Maintenance commands (repo root)
- Validate tracking consistency:
  - `python3 scripts/validate_tracking.py`
- Sync GitHub issues snapshot (public API):
  - `scripts/sync_github_issues.sh PolPol45/polinews open`
