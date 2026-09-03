"""
GitCompass — FastAPI application entry point.

No CORS middleware is configured for local development because the Vite
dev server proxies /api requests to this backend (same-origin from the
browser's perspective). CORS will be added with explicit origin
allowlisting when deploying to production.
"""

from contextlib import asynccontextmanager
import logging

# pyrefly: ignore [missing-import]
from fastapi import FastAPI

from app.config import settings

# ── Logging ───────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger("gitcompass")


# ── Lifespan ──────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hooks."""
    logger.info("🧭 %s starting up", settings.APP_NAME)
    logger.info("   Supabase URL: %s", settings.SUPABASE_URL)
    yield
    logger.info("🧭 %s shutting down", settings.APP_NAME)


# ── App ───────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Transform a GitHub repository's Git history into analytical intelligence.",
    version="0.1.0",
    lifespan=lifespan,
)

from app.routers import health, repositories, analytics, ai, evolution

# Mount routers
app.include_router(health.router)
app.include_router(repositories.router)
app.include_router(analytics.router)
app.include_router(ai.router)
app.include_router(evolution.router)


@app.get("/")
async def root():
    """Redirect to API docs for convenience during development."""
    return {"message": f"Welcome to {settings.APP_NAME}", "docs": "/docs"}
