"""
AI Router — Exposes endpoints for Gemini AI intelligence.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import json

from app.dependencies import CurrentUser, UserDB
from app.routers.analytics import get_repository_hotspots, get_bus_factor_analytics
from app.services.ai_service import generate_evolution_summary, detect_architecture_shifts, answer_qa

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AISummaryResponse(BaseModel):
    summary: str

class ChatRequest(BaseModel):
    question: str
    
class ChatResponse(BaseModel):
    answer: str


async def get_or_create_cache(db, repo_id: str, latest_sha: str, analysis_type: str, generator_coro):
    """Helper to fetch from ai_analysis_cache or generate and cache."""
    # Try to fetch from cache
    cache_res = db.table("ai_analysis_cache").select("*").eq("repo_id", repo_id).eq("analysis_type", analysis_type).execute()
    
    if cache_res.data and cache_res.data[0]["latest_sha"] == latest_sha:
        return cache_res.data[0]["content"]

    # Generate new content
    content = await generator_coro()
    
    # Upsert into cache
    if cache_res.data:
        db.table("ai_analysis_cache").update({
            "latest_sha": latest_sha,
            "content": content
        }).eq("id", cache_res.data[0]["id"]).execute()
    else:
        db.table("ai_analysis_cache").insert({
            "repo_id": repo_id,
            "analysis_type": analysis_type,
            "latest_sha": latest_sha,
            "content": content
        }).execute()
        
    return content


@router.post("/summary/{repo_id}", response_model=AISummaryResponse)
async def get_ai_summary(repo_id: str, user: CurrentUser, db: UserDB):
    """Generates or fetches cached AI summary of repository evolution."""
    repo_res = db.table("repositories").select("name, latest_commit_sha").eq("id", repo_id).execute()
    if not repo_res.data:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo_name = repo_res.data[0]["name"]
    latest_sha = repo_res.data[0].get("latest_commit_sha") or "unknown"

    async def generate():
        hotspots = await get_repository_hotspots(repo_id, user, db)
        bus_data = await get_bus_factor_analytics(repo_id, user, db)
        return await generate_evolution_summary(
            repo_name=repo_name,
            hotspots=[h.model_dump() for h in hotspots],
            bus_factor=bus_data["repo_bus_factor"],
        )

    summary_text = await get_or_create_cache(db, repo_id, latest_sha, "summary", generate)
    return {"summary": summary_text}


@router.post("/shifts/{repo_id}")
async def get_architecture_shifts(repo_id: str, user: CurrentUser, db: UserDB):
    """Detects architecture shifts using Gemini. Limited to repos with <= MAX_COMMITS."""
    repo_res = db.table("repositories").select("name, total_commits, latest_commit_sha").eq("id", repo_id).execute()
    if not repo_res.data:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo_name = repo_res.data[0]["name"]
    total_commits = repo_res.data[0]["total_commits"]
    latest_sha = repo_res.data[0].get("latest_commit_sha") or "unknown"

    async def generate():
        # Fetch significant commits (e.g. feat, refactor, fix) for context
        commits_res = db.table("commits").select("author_name, committed_at, message").eq("repo_id", repo_id).in_("commit_type", ["feat", "refactor", "fix"]).order("committed_at", desc=False).limit(200).execute()
        
        try:
            shifts = await detect_architecture_shifts(
                repo_name=repo_name,
                total_commits=total_commits,
                significant_commits=commits_res.data or []
            )
            return shifts
        except ValueError as e:
            # Re-raise as HTTP Exception for the 500 commit limit or missing key
            raise HTTPException(status_code=400, detail=str(e))

    shifts_data = await get_or_create_cache(db, repo_id, latest_sha, "shifts", generate)
    return {"shifts": shifts_data}


@router.post("/chat/{repo_id}", response_model=ChatResponse)
async def ask_chat_assistant(repo_id: str, payload: ChatRequest, user: CurrentUser, db: UserDB):
    """Answers Q&A questions about the repository (Ephemeral, not cached)."""
    repo_res = db.table("repositories").select("name, latest_commit_sha").eq("id", repo_id).execute()
    if not repo_res.data:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo_name = repo_res.data[0]["name"]
    latest_sha = repo_res.data[0].get("latest_commit_sha") or "unknown"

    # Fetch the cached summary to use as context for the chat
    cache_res = db.table("ai_analysis_cache").select("content").eq("repo_id", repo_id).eq("analysis_type", "summary").eq("latest_sha", latest_sha).execute()
    context = cache_res.data[0]["content"] if cache_res.data else "No summary context available."

    answer_text = await answer_qa(repo_name, payload.question, context)
    return {"answer": answer_text}
