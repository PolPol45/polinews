# source_policy_v1

Version: `2026-03-14-v1`
Owner: Founder (policy decisions) + Freelance (runtime enforcement + weekly review)
Status: APPROVED — locked for MVP pilot

---

## Goals
- Exclude low-quality, clickbait, and politically unreliable sources.
- Keep attribution clear and auditable on every story page.
- Maintain a minimum quality floor for quiz generation (garbage-in = garbage quiz).

---

## Policy fields per domain

| Field | Type | Description |
|---|---|---|
| `domain` | TEXT | Bare domain, e.g. `dailymail.co.uk` |
| `status` | ENUM | `allow`, `watch`, `deny` |
| `reputation_score` | INTEGER 0–100 | Quality signal — see scoring guide below |
| `last_reviewed_at` | DATE | Last checkpoint review date |
| `notes` | TEXT | Reason for current status |

---

## Runtime rules

- **Drop** all items where source domain has `status = deny`. Do not log to stories table.
- **Accept but flag** items where source domain has `status = watch`. Insert into stories with `source_watch_flag = true`.
- **Minimum reputation score for story inclusion: 60.** Items from domains with `reputation_score < 60` are rejected even if `status = allow`.
- Every story requires at least 1 source with `status = allow` and `reputation_score >= 60`.
- Unknown domains (not in the policy table) default to `status = watch` and `reputation_score = 50` until reviewed.

---

## Initial blocklist — `status = deny`

Effective immediately. These domains are denied at ingestion time.

| Domain | Reason |
|---|---|
| `buzzfeed.com` | Clickbait-first editorial model, unreliable sourcing |
| `dailymail.co.uk` | Chronic accuracy issues, misleading headlines |
| `breitbart.com` | Systematic misinformation, no editorial standards |
| `infowars.com` | Conspiracy content, banned from major platforms |
| `naturalnews.com` | Health misinformation, repeatedly flagged by fact-checkers |
| `thegatewaypundit.com` | Repeated misinformation, electoral fraud narratives |
| `rt.com` | State-controlled propaganda outlet (Russian state media) |
| `sputniknews.com` | State-controlled propaganda outlet (Russian state media) |

> **Note:** This list is intentionally short for MVP. New denials are added only at scheduled checkpoints — not ad hoc — to avoid policy drift. Freelance executes the weekly review and proposes changes; Founder approves before any status change takes effect.

---

## Reputation score guide

Scores are assigned manually during weekly review based on:

| Score range | Meaning | Examples |
|---|---|---|
| 80–100 | Tier 1 — major verified outlet | Reuters, AP, BBC, NYT, FT, The Economist |
| 60–79 | Tier 2 — reliable regional or specialist | Politico, Ars Technica, The Verge, Repubblica |
| 40–59 | Watch zone — use with caution | Aggregators, newer outlets, single-byline sites |
| 0–39 | Reject — below quality floor | Clickbait, no byline, unverifiable sources |

---

## Review cadence

- **Weekly review during pilot:** every 7 days, Freelance pulls top 50 domains by story volume from the past week and reviews status + score.
- **Promote/demote** only at checkpoint — never between checkpoints — to prevent policy drift.
- **Emergency deny** (e.g. active misinformation campaign): Founder can override at any time by direct edit to this file + commit. Must be noted in `checkpoints.md`.

---

## Changelog

| Date | Change | Author |
|---|---|---|
| 2026-03-14 | v1 created — initial blocklist (8 domains), min score 60, weekly review assigned to Freelance | Founder |
