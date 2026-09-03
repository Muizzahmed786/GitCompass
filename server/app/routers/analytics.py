"""
Analytics router — Phase 4.5 Deep Architectural Analytics.

Provides endpoints for accessing aggregated Git history analytics:
- Hotspots & Churn (with Time Machine date & conventional commit filters)
- Temporal Coupling Co-Change Matrix
- Bus Factor & Knowledge Loss Index
- Analytics Overview Summary
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status

from app.dependencies import CurrentUser, UserDB
from app.schemas.analytics import (
    HotspotResponse,
    TemporalCouplingItem,
    BusFactorResponse,
    SummaryAnalyticsResponse,
)

logger = logging.getLogger("gitcompass.routers.analytics")

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/{repo_id}/hotspots", response_model=List[HotspotResponse])
async def get_repository_hotspots(
    repo_id: str,
    user: CurrentUser,
    db: UserDB,
    start_date: Optional[str] = Query(None, description="ISO start date for Time Machine filter"),
    end_date: Optional[str] = Query(None, description="ISO end date for Time Machine filter"),
    commit_type: Optional[str] = Query(None, description="Conventional commit type filter (e.g. feat, fix)"),
):
    """Get hotspot analytics for a repository.

    Supports Time Machine date filtering and Conventional Commit classification.
    """
    try:
        # Check repository ownership
        repo = db.table("repositories").select("id").eq("id", repo_id).execute()
        if not repo.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Repository {repo_id} not found",
            )
            
        from app.services.analytics_service import calculate_hotspots
        results = await calculate_hotspots(db, repo_id, start_date, end_date, commit_type)
        return results

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Failed to fetch hotspots for repo %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error fetching hotspots: {exc}",
        )


@router.get("/{repo_id}/temporal-coupling", response_model=List[TemporalCouplingItem])
async def get_temporal_coupling(
    repo_id: str,
    user: CurrentUser,
    db: UserDB,
    threshold: float = Query(0.5, ge=0.1, le=1.0, description="Minimum co-change degree ratio"),
    max_commit_files: int = Query(50, description="Max files per commit to filter noise"),
):
    """Calculates temporal coupling (co-change matrix) for files frequently modified together."""
    try:
        from app.services.analytics_service import calculate_temporal_coupling
        results = await calculate_temporal_coupling(db, repo_id, threshold, max_commit_files)
        return results

    except Exception as exc:
        logger.error("Failed to compute temporal coupling for repo %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing temporal coupling: {exc}",
        )


@router.get("/{repo_id}/bus-factor", response_model=BusFactorResponse)
async def get_bus_factor_analytics(repo_id: str, user: CurrentUser, db: UserDB):
    """Calculates repository Bus Factor index and identifies Knowledge Loss Orphan Risk files."""
    try:
        from app.services.analytics_service import calculate_bus_factor
        results = await calculate_bus_factor(db, repo_id)
        return results

    except Exception as exc:
        logger.error("Failed to compute bus factor for repo %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing bus factor: {exc}",
        )


@router.get("/{repo_id}/summary", response_model=SummaryAnalyticsResponse)
async def get_analytics_summary(repo_id: str, user: CurrentUser, db: UserDB):
    """Returns overview analytics summary including commit types, Bus Factor, and coupling stats."""
    try:
        from app.services.analytics_service import calculate_summary
        results = await calculate_summary(db, repo_id)
        return results

    except Exception as exc:
        logger.error("Failed to compute summary for repo %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing summary analytics: {exc}",
        )

