"""
Analytics router.

Provides endpoints for accessing aggregated Git history analytics,
such as churn rates and contributor ownership scores.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.dependencies import CurrentUser, UserDB

logger = logging.getLogger("gitcompass.routers.analytics")

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


class HotspotResponse(BaseModel):
    file_path: str
    commits_count: int
    total_insertions: int
    total_deletions: int
    authors: List[str]
    is_deleted: bool


@router.get("/{repo_id}/hotspots", response_model=List[HotspotResponse])
async def get_repository_hotspots(repo_id: str, user: CurrentUser, db: UserDB):
    """Get the hotspot analytics (churn & contributors) for a repository.

    Aggregates file modifications in Python by paginating through file_diffs.
    This bypasses PostgREST schema cache and RPC signature mismatch issues.
    """
    try:
        # Check if repo exists and belongs to user
        repo = db.table("repositories").select("id").eq("id", repo_id).execute()
        if not repo.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )

        hotspots_map = {}
        page_size = 1000
        
        # Paginate to fetch all file diffs for this repo
        for offset in range(0, 100000, page_size):
            res = (
                db.table("file_diffs")
                .select("file_path, insertions, deletions, is_deleted, commits!inner(author_name)")
                .eq("repo_id", repo_id)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            
            if not res.data:
                break
                
            for row in res.data:
                path = row["file_path"]
                if path not in hotspots_map:
                    hotspots_map[path] = {
                        "file_path": path,
                        "commits_count": 0,
                        "total_insertions": 0,
                        "total_deletions": 0,
                        "authors": set(),
                        "is_deleted": row.get("is_deleted", False)
                    }
                
                hotspot = hotspots_map[path]
                hotspot["commits_count"] += 1
                hotspot["total_insertions"] += row.get("insertions", 0)
                hotspot["total_deletions"] += row.get("deletions", 0)
                
                commit_data = row.get("commits")
                if commit_data and commit_data.get("author_name"):
                    hotspot["authors"].add(commit_data["author_name"])

        # Convert to list and sort by churn
        results = []
        for path, data in hotspots_map.items():
            data["authors"] = list(data["authors"])
            results.append(data)
            
        results.sort(key=lambda x: x["commits_count"], reverse=True)
        return results

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch hotspots for repo %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error fetching hotspots: {exc}",
        )
