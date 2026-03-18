from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class CollectorLogger:
    def __init__(self, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        self.run_log_path = log_dir / "ingestion_runs.log"
        self.reject_log_path = log_dir / "ingestion_rejects.log"
        self.run_log_path.touch(exist_ok=True)
        self.reject_log_path.touch(exist_ok=True)

    def log_run(
        self,
        *,
        feed_id: str,
        start_ts: str,
        end_ts: str,
        fetched_count: int,
        accepted_count: int,
        rejected_count: int,
        error_class: str,
    ) -> None:
        line = (
            f"{feed_id},{start_ts},{end_ts},{fetched_count},"
            f"{accepted_count},{rejected_count},{error_class}"
        )
        self._append(self.run_log_path, line)
        print(f"[RUN] {line}")

    def log_reject(self, *, feed_id: str, item_ref: str, reason_code: str, reject_ts: str) -> None:
        safe_ref = item_ref.replace("\n", " ").replace(",", ";")[:200]
        line = f"{feed_id},{safe_ref},{reason_code},{reject_ts}"
        self._append(self.reject_log_path, line)
        print(f"[REJECT] {line}")

    @staticmethod
    def _append(path: Path, line: str) -> None:
        with path.open("a", encoding="utf-8") as fp:
            fp.write(line + "\n")
