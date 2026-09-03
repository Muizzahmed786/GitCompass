"""
AI Router — Exposes endpoints for Gemini AI intelligence.
"""

import logging
from collections import defaultdict
from enum import Enum
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException
from typing import Any, List, Dict, Optional
import re

from app.dependencies import CurrentUser, UserDB
from app.schemas.ai import (
    AIModelChoice,
    AIRequest,
    AISummaryResponse,
    ChatMessage,
    ChatRequest,
    Citation,
    ChatResponse,
)
from app.services.ai_service import (
    generate_evolution_summary,
    detect_architecture_shifts,
    answer_qa,
    generate_development_story,
)
from app.services.ai_cache import check_cache, save_cache
from app.services.chat_retrieval import resolve_chat_evidence
from app.services.evidence_assembler import assemble_evidence
from datetime import datetime


logger = logging.getLogger("gitcompass.routers.ai")

router = APIRouter(prefix="/api/ai", tags=["ai"])


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
            hit, cached = check_cache(db, repo_id, "summary", selected_model, latest_sha, force_refresh)
            if hit:
                return cached

        evidence = assemble_evidence(repo_id, db)

        summary_data = await generate_evolution_summary(
            repo_name=repo_name,
            evidence=evidence,
            selected_model=selected_model
        )
        
        save_cache(db, repo_id, "summary", selected_model, latest_sha, summary_data)

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
            hit, cached = check_cache(db, repo_id, "shifts", selected_model, latest_sha, force_refresh)
            if hit:
                return cached

        evidence = assemble_evidence(repo_id, db)

        shifts = await detect_architecture_shifts(
            repo_name=repo_name,
            evidence=evidence,
            selected_model=selected_model
        )
        
        save_cache(db, repo_id, "shifts", selected_model, latest_sha, shifts)

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

        specific_slice, supplied_paths = resolve_chat_evidence(db, repo_id, evidence, payload.history, payload.page_context)

        history_dicts = [{"role": msg.role, "content": msg.content} for msg in payload.history]
        
        # Pass page_context and specific_slice down
        qa_result = await answer_qa(
            repo_name=repo_name,
            history=history_dicts,
            evidence=evidence,
            page_context=payload.page_context,
            specific_slice=specific_slice
        )
        
        # Citation Validation
        validated_citations = []
        for cit in qa_result.get("citations", []):
            cit_path = cit.get("path")
            if cit.get("type") == "file" and cit_path in supplied_paths:
                validated_citations.append(Citation(type="file", path=cit_path))
                
        return ChatResponse(answer=qa_result.get("answer", ""), citations=validated_citations)

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
            hit, cached = check_cache(db, repo_id, "story", selected_model, latest_sha, force_refresh)
            if hit:
                return cached

        evidence = assemble_evidence(repo_id, db)

        story_data = await generate_development_story(
            repo_name=repo_name,
            evidence=evidence,
            selected_model=selected_model
        )
        
        save_cache(db, repo_id, "story", selected_model, latest_sha, story_data)

        return {"story": story_data}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Development story failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Development story generation failed: {exc}")


