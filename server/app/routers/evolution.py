"""
Evolution router — provides endpoints for repository evolution events and file lifecycle history.
"""

import logging
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, Query

from app.dependencies import CurrentUser, UserDB

logger = logging.getLogger("gitcompass.api.evolution")
router = APIRouter(prefix="/api/repositories/{repo_id}/evolution", tags=["Evolution"])

@router.get("/events")
async def get_evolution_events(
    repo_id: str,
    limit: int = Query(100, le=1000),
    offset: int = 0,
    user: CurrentUser = None,
    db: UserDB = None,
):
    """Retrieves deterministic historical evolution events for a repository."""
    try:
        res = db.table("repository_events").select("*").eq("repo_id", repo_id).order("event_date", desc=True).range(offset, offset + limit - 1).execute()
        return res.data
    except Exception as e:
        logger.error(f"Failed to fetch evolution events: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch evolution events")

@router.get("/files/{file_path:path}")
async def get_file_evolution(
    repo_id: str,
    file_path: str,
    user: CurrentUser = None,
    db: UserDB = None,
):
    """Retrieves the lifecycle of a specific file based on commits and file_diffs."""
    try:
        res = db.table("file_diffs").select(
            "is_rename, insertions, deletions, old_path, commits(sha, author_name, committed_at, message)"
        ).eq("repo_id", repo_id).eq("file_path", file_path).execute()
        
        diffs = res.data
        if not diffs:
            raise HTTPException(status_code=404, detail="File not found in history")
            
        valid_diffs = [d for d in diffs if d.get("commits")]
        valid_diffs.sort(key=lambda d: d["commits"]["committed_at"])
        
        if not valid_diffs:
            return {"file_path": file_path, "history": []}
            
        history = []
        total_insertions = 0
        total_deletions = 0
        
        for d in valid_diffs:
            c = d["commits"]
            total_insertions += d["insertions"]
            total_deletions += d["deletions"]
            history.append({
                "sha": c["sha"],
                "committed_at": c["committed_at"],
                "author_name": c["author_name"],
                "message": c["message"],
                "insertions": d["insertions"],
                "deletions": d["deletions"],
                "is_rename": d["is_rename"],
                "old_path": d.get("old_path")
            })
            
        return {
            "file_path": file_path,
            "created_at": history[0]["committed_at"],
            "last_modified": history[-1]["committed_at"],
            "total_commits": len(history),
            "total_insertions": total_insertions,
            "total_deletions": total_deletions,
            "history": history
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch file evolution: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch file evolution")

