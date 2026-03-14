#!/usr/bin/env python3
"""Validate consistency between master_tasks.csv and KANBAN_BOARD.md snapshot."""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "docs/mvp_offchain/tracking/master_tasks.csv"
KANBAN = ROOT / "docs/mvp_offchain/tracking/KANBAN_BOARD.md"

VALID_STATUS = {"NOT_STARTED", "IN_PROGRESS", "BLOCKED", "DONE"}


def parse_snapshot(text: str) -> dict[str, int]:
    patterns = {
        "NOT_STARTED": r"^- Backlog:\s*(\d+)\s*$",
        "IN_PROGRESS": r"^- In progress:\s*(\d+)\s*$",
        "BLOCKED": r"^- Blocked:\s*(\d+)\s*$",
        "DONE": r"^- Done:\s*(\d+)\s*$",
    }
    out: dict[str, int] = {}
    for line in text.splitlines():
        for key, pat in patterns.items():
            m = re.match(pat, line)
            if m:
                out[key] = int(m.group(1))
    return out


def main() -> int:
    if not MASTER.exists() or not KANBAN.exists():
        print("ERROR: tracking files not found")
        return 1

    rows = list(csv.DictReader(MASTER.open()))
    ids = [r["id"].strip() for r in rows]

    errors: list[str] = []

    dup_ids = [task_id for task_id, c in Counter(ids).items() if c > 1]
    if dup_ids:
        errors.append(f"duplicate task IDs: {', '.join(dup_ids)}")

    bad_status = [r["id"] for r in rows if r["status"].strip() not in VALID_STATUS]
    if bad_status:
        errors.append(f"invalid status values for: {', '.join(bad_status)}")

    counts = Counter(r["status"].strip() for r in rows)
    expected = {
        "NOT_STARTED": counts.get("NOT_STARTED", 0),
        "IN_PROGRESS": counts.get("IN_PROGRESS", 0),
        "BLOCKED": counts.get("BLOCKED", 0),
        "DONE": counts.get("DONE", 0),
    }

    snapshot = parse_snapshot(KANBAN.read_text())
    if snapshot != expected:
        errors.append(f"kanban snapshot mismatch: expected={expected} got={snapshot}")

    print(f"master_tasks rows: {len(rows)}")
    print(f"status counts: {dict(expected)}")

    if errors:
        print("VALIDATION: FAIL")
        for e in errors:
            print(f"- {e}")
        return 1

    print("VALIDATION: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
