"""
Health-check endpoints for GitCompass.

Three tiers of health verification:
  /api/health       — basic heartbeat (public)
  /api/health/db    — Supabase connectivity (public)
  /api/health/auth  — end-to-end JWT validation (protected)
"""

from datetime import datetime, timezone

from fastapi import APIRouter
from supabase import create_client

from app.config import settings
from app.dependencies import CurrentUser

router = APIRouter(prefix="/api/health", tags=["health"])


@router.get("")
async def health():
    """Basic heartbeat — confirms the FastAPI process is running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": settings.APP_NAME,
    }


@router.get("/db")
async def health_db():
    """Verify Supabase connectivity with a lightweight query.

    Uses the anon key — this is a public endpoint that just confirms
    the database is reachable, not that any specific data exists.
    """
    try:
        client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        # A simple RPC or table ping; querying profiles with limit 0
        # is the lightest possible roundtrip.
        client.table("profiles").select("id", count="exact").limit(0).execute()
        return {
            "status": "ok",
            "supabase": "connected",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "supabase": "unreachable",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


@router.get("/auth")
async def health_auth(user: CurrentUser):
    """Protected endpoint — validates the full JWT auth chain.

    If this returns 200, the caller's token is valid and the dependency
    pipeline (header extraction → JWT decode → audience check) works
    end-to-end.
    """
    return {
        "status": "ok",
        "user_id": user.get("sub"),
        "email": user.get("email"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
