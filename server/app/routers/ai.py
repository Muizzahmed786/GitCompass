"""
AI Router — Exposes endpoints for Gemini AI intelligence.
"""

import logging
from collections import defaultdict
from enum import Enum
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, List, Dict

from app.dependencies import CurrentUser, UserDB
from app.services.ai_service import (
    generate_evolution_summary,
    detect_architecture_shifts,
    answer_qa,
    generate_development_story,
)
from app.services.evidence_assembler import assemble_evidence
from datetime import datetime


logger = logging.getLogger("gitcompass.routers.ai")

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AIModelChoice(str, Enum):
    auto = "auto"
    gemini_flash = "gemini_flash"
    gemini_flash_lite = "gemini_flash_lite"
    groq = "groq"

class AIRequest(BaseModel):
    model: AIModelChoice = AIModelChoice.auto
    force_refresh: bool = False

class AISummaryResponse(BaseModel):
    summary: Any = None
    is_cached: bool = False
    is_stale: bool = False

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    history: List[ChatMessage]

class ChatResponse(BaseModel):
    answer: str


@router.post("/summary/{repo_id}", response_model=AISummaryResponse)
async def get_ai_summary(repo_id: str, user: CurrentUser, db: UserDB, payload: AIRequest = None):
    """Generates AI summary of repository evolution using Gemini."""
    try:
        repo_res = db.table("repositories").select("name, total_commits, latest_commit_sha").eq("id", repo_id).execute()
        if not repo_res.data:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_name = repo_res.data[0].get("name") or "Unknown"
        total_commits = repo_res.data[0].get("total_commits", 0)
        latest_sha = repo_res.data[0].get("latest_commit_sha") or "unknown"

        selected_model = payload.model.value if payload else "auto"
        force_refresh = payload.force_refresh if payload else False

        if not force_refresh:
            cache_res = db.table("ai_analysis_cache").select("content, latest_sha").eq("repo_id", repo_id).eq("analysis_type", "summary").eq("model", selected_model).execute()
            if not cache_res.data:
                return {"summary": None, "is_cached": False, "is_stale": False}
            
            cached_content = cache_res.data[0]["content"]
            is_stale = (cache_res.data[0].get("latest_sha") != latest_sha)
            
            return {"summary": cached_content, "is_cached": True, "is_stale": is_stale}

        evidence = assemble_evidence(repo_id, db)

        summary_data = await generate_evolution_summary(
            repo_name=repo_name,
            evidence=evidence,
            selected_model=selected_model
        )
        
        # Save to cache
        db.table("ai_analysis_cache").upsert({
            "repo_id": repo_id,
            "analysis_type": "summary",
            "model": selected_model,
            "latest_sha": latest_sha,
            "content": summary_data
        }, on_conflict="repo_id,analysis_type,model").execute()

        return {"summary": summary_data}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("AI summary failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI summary generation failed: {exc}")


@router.post("/shifts/{repo_id}")
async def get_architecture_shifts(repo_id: str, user: CurrentUser, db: UserDB, payload: AIRequest = None):
    """Detects architecture shifts using Gemini. Limited to repos with <= MAX_COMMITS."""
    try:
        repo_res = db.table("repositories").select("name, total_commits, latest_commit_sha").eq("id", repo_id).execute()
        if not repo_res.data:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_name = repo_res.data[0].get("name") or "Unknown"
        total_commits = repo_res.data[0].get("total_commits") or 0
        latest_sha = repo_res.data[0].get("latest_commit_sha") or "unknown"

        selected_model = payload.model.value if payload else "auto"
        force_refresh = payload.force_refresh if payload else False

        if not force_refresh:
            cache_res = db.table("ai_analysis_cache").select("content, latest_sha").eq("repo_id", repo_id).eq("analysis_type", "shifts").eq("model", selected_model).execute()
            if not cache_res.data:
                return {"shifts": None, "is_cached": False, "is_stale": False}
            
            cached_content = cache_res.data[0]["content"]
            is_stale = (cache_res.data[0].get("latest_sha") != latest_sha)
            
            return {"shifts": cached_content, "is_cached": True, "is_stale": is_stale}

        evidence = assemble_evidence(repo_id, db)

        shifts = await detect_architecture_shifts(
            repo_name=repo_name,
            evidence=evidence,
            selected_model=selected_model
        )
        
        # Save to cache
        db.table("ai_analysis_cache").upsert({
            "repo_id": repo_id,
            "analysis_type": "shifts",
            "model": selected_model,
            "latest_sha": latest_sha,
            "content": shifts
        }, on_conflict="repo_id,analysis_type,model").execute()

        return {"shifts": shifts}

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as exc:
        logger.error("AI shifts failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI shift detection failed: {exc}")


@router.post("/chat/{repo_id}", response_model=ChatResponse)
async def ask_chat_assistant(repo_id: str, payload: ChatRequest, user: CurrentUser, db: UserDB):
    """Answers Q&A questions about the repository using its evidence model."""
    try:
        # Validate history size to prevent excessively large prompts
        if len(payload.history) > 20:
            raise HTTPException(status_code=400, detail="Conversation history too large (max 20 messages)")
            
        # Ensure all roles are valid and bounded
        total_history_len = 0
        for msg in payload.history:
            if msg.role not in ("user", "assistant"):
                raise HTTPException(status_code=400, detail="Invalid message role")
            if not msg.content.strip():
                raise HTTPException(status_code=400, detail="Message content cannot be empty")
            if len(msg.content) > 2000:
                raise HTTPException(status_code=400, detail="Individual message exceeds 2000 characters")
            total_history_len += len(msg.content)
            
        if total_history_len > 20000:
            raise HTTPException(status_code=400, detail="Total conversation history exceeds 20000 characters")

        repo_res = db.table("repositories").select("name").eq("id", repo_id).execute()
        if not repo_res.data:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_name = repo_res.data[0].get("name") or "Unknown"

        # Assemble authoritative evidence
        try:
            evidence = assemble_evidence(repo_id, db)
            evidence["evidence_status"] = "available"
        except Exception as e:
            logger.warning("Failed to assemble complete evidence for chat: %s", e)
            evidence = {"evidence_status": "unavailable"}

        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.history]
        
        answer_text = await answer_qa(repo_name, history_dicts, evidence)
        return {"answer": answer_text}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("AI chat failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI chat failed: {exc}")


@router.post("/story/{repo_id}")
async def get_development_story(repo_id: str, user: CurrentUser, db: UserDB, payload: AIRequest = None):
    """Generates a narrative development story based on monthly chronological Git aggregation."""
    try:
        repo_res = db.table("repositories").select("name, total_commits, latest_commit_sha").eq("id", repo_id).execute()
        if not repo_res.data:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_name = repo_res.data[0].get("name") or "Unknown"
        latest_sha = repo_res.data[0].get("latest_commit_sha") or "unknown"

        selected_model = payload.model.value if payload else "auto"
        force_refresh = payload.force_refresh if payload else False

        if not force_refresh:
            cache_res = db.table("ai_analysis_cache").select("content, latest_sha").eq("repo_id", repo_id).eq("analysis_type", "story").eq("model", selected_model).execute()
            if not cache_res.data:
                return {"story": None, "is_cached": False, "is_stale": False}
            
            cached_content = cache_res.data[0]["content"]
            is_stale = (cache_res.data[0].get("latest_sha") != latest_sha)
            
            return {"story": cached_content, "is_cached": True, "is_stale": is_stale}

        evidence = assemble_evidence(repo_id, db)

        story_data = await generate_development_story(
            repo_name=repo_name,
            evidence=evidence,
            selected_model=selected_model
        )
        
        # Save to cache
        db.table("ai_analysis_cache").upsert({
            "repo_id": repo_id,
            "analysis_type": "story",
            "model": selected_model,
            "latest_sha": latest_sha,
            "content": story_data
        }, on_conflict="repo_id,analysis_type,model").execute()

        return {"story": story_data}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Development story failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Development story generation failed: {exc}")


