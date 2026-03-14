# Checkpoints Log

## Governance Updates
- 2026-03-05: `G-03` approved by founder and marked `DONE`.
- 2026-03-05: `G-02` set to `BLOCKED` pending calendar integration.
- 2026-03-14: `W1-01` marked `DONE` after founder confirmation of `topics_v1` and validation of slug rules/description clarity.
- 2026-03-14: `W1-02` marked `DONE`. Registry structure validated (9 columns, no duplicate `feed_id`, `topic_slug` aligned to `topics_v1`), coverage validated (all topics present, >=1 active feed/topic, locale mix US/UK/IT), URL validation passed (30/30 valid RSS), freeze rule applied (`feed_<topic>_<country>` naming lock, changes only at checkpoints).
- 2026-03-14: `W1-03` marked `DONE`. Ingestion policy validated with all 5 required sections present (`Schedule`, `Networking controls`, `Acceptance checks per item`, `Stale mode`, `Logging requirements`), required parameters confirmed (refresh 15m + jitter +/-60s, timeout 8s, retries 3, backoff 1s/3s/9s, stale mode after 3 consecutive failures), and logging format confirmed sufficient for KPI/failure debugging (one line per feed run + one line per rejected item with reason code).
- 2026-03-14: `W1-04` marked `DONE`. Implemented Python RSS/Atom collector (`collector/rss_collector.py`) with run-once CLI, policy-conform fetch (timeout 8s, retries 3, backoff 1s/3s/9s, fixed user-agent), item validation, SQLite insert into `feed_items_raw`, run/reject structured logs, and stale-failure counter logging. Evidence run (`data/polinews_w104_final.db`, `logs/w104_final`): 30 active feeds processed, 3036 rows inserted, 30 run log lines, 0 reject lines.
- 2026-03-14: Business alignment v0.2 applied from `MVP.md` and `polinews_revenue_plan.docx`, with process updates reflected in planning artifacts (`master_tasks.csv`, `KANBAN_BOARD.md`, `calendar_4_weeks.md`) and technical specs (`data_model_mvp.sql`, `api_contract_mvp.md`, `kpi_spec_v1.md`, `reward_policy_v1.md`, `compliance_data_policy_v1.md`, `phase2_blockchain_architecture.md`). Current Week 1 outputs remain reusable for the updated model.
- 2026-03-14: `polinews_business_model_canvas.pdf` is image-based in local tooling; no reliable text extraction available in sandbox. Operational alignment was completed against the two text sources above, pending founder visual confirmation for any extra canvas-only nuances.

## Template
- Date:
- Checkpoint ID:
- Completed tasks:
- Blocked tasks:
- KPI snapshot:
- Risks:
- Decisions:
- Evidence links:

## W1-12
- Date:
- Status:
- Notes:

## W2-13
- Date:
- Status:
- Notes:

## W3-12
- Date:
- Status:
- Notes:

## W4-10
- Date:
- Status:
- Notes:
