"""
Repositories router.

Provides endpoints for creating, listing, retrieving, and deleting repositories.
Triggering repository mining delegates long-running git operations to FastAPI BackgroundTasks.
"""

import logging
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from app.dependencies import CurrentUser, UserDB
from app.schemas.repository import RepositoryCreate, RepositoryListResponse, RepositoryResponse
from app.services.cloner import parse_github_url
from app.services.miner import mine_repository_task

logger = logging.getLogger("gitcompass.routers.repositories")

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_repository(
    payload: RepositoryCreate,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: UserDB,
):
    """Add a new GitHub repository to GIT Compass for analysis.

    Inserts a repository record with status 'pending' and immediately kicks off
    background cloning & mining. Returns HTTP 202 Accepted.
    """
    user_id = user["sub"]
    url_str = payload.github_url

    try:
        _, repo_name = parse_github_url(url_str)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    # Standardize URL to always end with .git for consistent DB querying
    url_str = url_str.strip()
    if not url_str.endswith(".git") and not url_str.startswith("git@"):
        url_str = f"{url_str}.git"

    # Check if this user is already tracking this repository
    existing = (
        db.table("repositories")
        .select("id, status")
        .eq("user_id", user_id)
        .eq("github_url", url_str)
        .execute()
    )
    if existing.data:
        existing_repo = existing.data[0]
        # Atomically wipe the existing repository and all its tracked history
        # (relies on ON DELETE CASCADE constraints)
        logger.info("Wiping existing repository %s to reload new branch", existing_repo["id"])
        db.table("repositories").delete().eq("id", existing_repo["id"]).execute()

    # Insert new pending repository record
    new_repo_data = {
        "user_id": user_id,
        "github_url": url_str,
        "name": repo_name,
        "status": "pending",
    }
    
    if payload.branch:
        new_repo_data["default_branch"] = payload.branch

    try:
        res = db.table("repositories").insert(new_repo_data).execute()
        if not res.data:
            raise RuntimeError("Database returned no data after insert")
        repo_record = res.data[0]
    except Exception as exc:
        logger.error("Failed to insert repository record: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error creating repository: {exc}",
        )

    repo_id = repo_record["id"]

    # Trigger asynchronous mining background task
    background_tasks.add_task(mine_repository_task, repo_id, url_str, user_id, payload.branch)
    logger.info("Enqueued background task for repository %s (%s)", repo_id, url_str)

    return repo_record


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(user: CurrentUser, db: UserDB):
    """List all repositories owned by the current authenticated user."""
    try:
        res = db.table("repositories").select("*").order("created_at", desc=True).execute()
        return {"repositories": res.data or [], "count": len(res.data or [])}
    except Exception as exc:
        logger.error("Failed to list repositories: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error listing repositories: {exc}",
        )


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(repo_id: str, user: CurrentUser, db: UserDB):
    """Get details of a specific repository by ID."""
    try:
        res = db.table("repositories").select("*").eq("id", repo_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        return res.data[0]
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to get repository %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {exc}",
        )


@router.delete("/{repo_id}")
async def delete_repository(repo_id: str, user: CurrentUser, db: UserDB):
    """Delete a repository and its mined data."""
    try:
        res = db.table("repositories").delete().eq("id", repo_id).execute()
        if not res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
        return {"status": "deleted", "id": repo_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to delete repository %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error deleting repository: {exc}",
        )
