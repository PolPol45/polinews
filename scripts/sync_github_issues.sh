#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${1:-PolPol45/polinews}"
STATE="${2:-open}"
OUT_JSON="${ROOT_DIR}/docs/mvp_offchain/tracking/github_issues_snapshot.json"
OUT_MD="${ROOT_DIR}/docs/mvp_offchain/tracking/github_issues_snapshot.md"
NOW_UTC="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"

mkdir -p "$(dirname "${OUT_JSON}")"

# Public GitHub API (works without auth for public repos, rate-limited).
curl -sS "https://api.github.com/repos/${REPO}/issues?state=${STATE}&per_page=100" > "${OUT_JSON}"

python3 - <<'PY' "${OUT_JSON}" "${OUT_MD}" "${REPO}" "${STATE}" "${NOW_UTC}"
from __future__ import annotations

import json
import sys
from pathlib import Path

src, dst, repo, state, now = sys.argv[1:6]
issues = json.loads(Path(src).read_text())

# GitHub issues endpoint also returns PRs; exclude PRs.
issues = [i for i in issues if "pull_request" not in i]

lines = []
lines.append(f"# GitHub Issues Snapshot - {repo}")
lines.append("")
lines.append(f"- Generated: {now}")
lines.append(f"- State filter: `{state}`")
lines.append(f"- Issue count: {len(issues)}")
lines.append("")

if not issues:
    lines.append("No issues found for this filter.")
else:
    lines.append("| # | Title | Labels | Created | URL |")
    lines.append("|---:|---|---|---|---|")
    for item in issues:
        labels = ", ".join(l["name"] for l in item.get("labels", [])) or "-"
        title = item.get("title", "").replace("|", "\\|")
        number = item.get("number", "")
        created = (item.get("created_at") or "")[:10]
        url = item.get("html_url", "")
        lines.append(f"| {number} | {title} | {labels} | {created} | {url} |")

Path(dst).write_text("\n".join(lines) + "\n")
PY

echo "Issue snapshot written: ${OUT_MD}"
echo "Raw JSON written: ${OUT_JSON}"
