"""
Main FastAPI application.

Registers all routers and mounts lifecycle events.
The scheduler can optionally run in-process (controlled by START_SCHEDULER env var).
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from polinews.api.analytics import router as analytics_router
from polinews.api.auth import router as auth_router
from polinews.api.dashboard import router as dashboard_router
from polinews.api.feed_story import feed_router, story_router
from polinews.api.quiz import router as quiz_router
from polinews.api.rewards import router as rewards_router
from polinews.api.sessions import router as sessions_router
from polinews.config import API_HOST, API_PORT, CORS_ORIGINS, DB_PATH
from polinews.db.connection import connect_db
from polinews.db.schema import ensure_schema

log = logging.getLogger("polinews.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup / shutdown events."""
    # Ensure DB schema on startup
    conn = connect_db(DB_PATH)
    ensure_schema(conn)
    conn.close()
    log.info("[api] DB schema verified — db_path=%s", DB_PATH)

    # Optionally embed scheduler in-process
    scheduler = None
    if os.getenv("START_SCHEDULER", "0") == "1":
        from polinews.worker.scheduler import make_background_scheduler
        scheduler = make_background_scheduler()
        scheduler.start()
        log.info("[api] embedded scheduler started")

    yield

    if scheduler is not None:
        scheduler.shutdown(wait=False)
        log.info("[api] embedded scheduler stopped")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Poli-News API",
        version="0.3.0",
        description="Proof-of-Reading incentive layer — off-chain backend",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(auth_router)
    app.include_router(feed_router)
    app.include_router(story_router)
    app.include_router(quiz_router)
    app.include_router(rewards_router)
    app.include_router(dashboard_router)
    app.include_router(sessions_router)
    app.include_router(analytics_router)

    # Health
    @app.get("/health", tags=["ops"])
    def health() -> dict[str, Any]:
        db_ok = DB_PATH.exists()
        return {
            "status": "ok" if db_ok else "degraded",
            "db_path": str(DB_PATH),
            "db_exists": db_ok,
            "version": "0.3.0",
        }

    return app


app = create_app()


def run_dev_server() -> None:
    import uvicorn
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    uvicorn.run("polinews.api.app:app", host=API_HOST, port=API_PORT, reload=True)
