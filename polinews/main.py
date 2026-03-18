"""
Entry points for the Poli-News CLI commands.

  polinews-serve   → starts the FastAPI server (uvicorn)
  polinews-collect → starts the blocking scheduler worker
"""
from __future__ import annotations

import logging
import sys


def serve() -> None:
    """Entry point: polinews-serve"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        import uvicorn
    except ImportError:
        print("[ERROR] uvicorn not installed. Run: pip install uvicorn[standard]", file=sys.stderr)
        sys.exit(1)

    from polinews.config import API_HOST, API_PORT
    uvicorn.run(
        "polinews.api.app:app",
        host=API_HOST,
        port=API_PORT,
        reload=False,
        log_level="info",
    )


def collect() -> None:
    """Entry point: polinews-collect"""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from polinews.worker.scheduler import start_blocking_scheduler
    start_blocking_scheduler()
