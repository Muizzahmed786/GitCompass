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
    commit_types: Dict[str, int] = {}
    top_author: Optional[str] = None
    top_author_share: float = 0.0
    is_orphan_risk: bool = False


class TemporalCouplingItem(BaseModel):
    file_a: str
    file_b: str
    co_changes: int
    degree: float


class BusFactorResponse(BaseModel):
    repo_bus_factor: int
    top_contributors: Dict[str, int]
    orphan_risk_files: List[dict]


class SummaryAnalyticsResponse(BaseModel):
    total_commits: int
    total_files: int
    bus_factor: int
    commit_types_distribution: Dict[str, int]
    total_coupled_pairs: int
    orphan_files_count: int


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

        hotspots_map = {}
        cutoff_90_days = datetime.now(timezone.utc) - timedelta(days=90)
        page_size = 1000

        # Paginate to fetch file diffs joined with commit details
        for offset in range(0, 100000, page_size):
            query = (
                db.table("file_diffs")
                .select("file_path, insertions, deletions, is_deleted, commits!inner(author_name, committed_at, commit_type, message)")
                .eq("repo_id", repo_id)
            )

            if start_date:
                query = query.gte("commits.committed_at", start_date)
            if end_date:
                query = query.lte("commits.committed_at", end_date)
            if commit_type and commit_type != "all":
                query = query.eq("commits.commit_type", commit_type)

            res = query.range(offset, offset + page_size - 1).execute()

            if not res.data:
                break

            for row in res.data:
                path = row["file_path"]
                commit_info = row.get("commits") or {}
                author = commit_info.get("author_name") or "Unknown"
                c_type = commit_info.get("commit_type") or "other"
                committed_at_str = commit_info.get("committed_at")

                if path not in hotspots_map:
                    hotspots_map[path] = {
                        "file_path": path,
                        "commits_count": 0,
                        "total_insertions": 0,
                        "total_deletions": 0,
                        "authors_map": defaultdict(int),
                        "commit_types": defaultdict(int),
                        "latest_commit_date": None,
                        "is_deleted": row.get("is_deleted", False),
                    }

                hotspot = hotspots_map[path]
                hotspot["commits_count"] += 1
                hotspot["total_insertions"] += row.get("insertions", 0)
                hotspot["total_deletions"] += row.get("deletions", 0)
                hotspot["authors_map"][author] += 1
                hotspot["commit_types"][c_type] += 1

                if committed_at_str:
                    try:
                        c_date = datetime.fromisoformat(committed_at_str.replace("Z", "+00:00"))
                        if not hotspot["latest_commit_date"] or c_date > hotspot["latest_commit_date"]:
                            hotspot["latest_commit_date"] = c_date
                    except Exception:
                        pass

        # Build response objects
        results = []
        for path, data in hotspots_map.items():
            authors_list = list(data["authors_map"].keys())
            total_c = data["commits_count"]

            top_author = None
            top_author_share = 0.0
            if data["authors_map"] and total_c > 0:
                top_author, top_commits = max(data["authors_map"].items(), key=lambda x: x[1])
                top_author_share = round(top_commits / total_c, 3)

            # Orphan Risk: Top author share > 80% or latest commit older than 90 days
            latest_date = data.get("latest_commit_date")
            is_stale = latest_date and (latest_date < cutoff_90_days)
            is_orphan = (top_author_share >= 0.80) or bool(is_stale)

            results.append({
                "file_path": path,
                "commits_count": total_c,
                "total_insertions": data["total_insertions"],
                "total_deletions": data["total_deletions"],
                "authors": authors_list,
                "is_deleted": data["is_deleted"],
                "commit_types": dict(data["commit_types"]),
                "top_author": top_author,
                "top_author_share": top_author_share,
                "is_orphan_risk": is_orphan,
            })

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
        page_size = 1000
        commit_files_map = defaultdict(set)
        file_commit_counts = defaultdict(int)

        # Step 1: Group file diffs by commit_id
        for offset in range(0, 100000, page_size):
            res = (
                db.table("file_diffs")
                .select("commit_id, file_path")
                .eq("repo_id", repo_id)
                .range(offset, offset + page_size - 1)
                .execute()
            )
            if not res.data:
                break
            for row in res.data:
                c_id = row["commit_id"]
                f_path = row["file_path"]
                commit_files_map[c_id].add(f_path)
                file_commit_counts[f_path] += 1

        # Step 2: Calculate co-change frequency for pairs
        co_changes = defaultdict(int)

        for c_id, files in commit_files_map.items():
            if len(files) > max_commit_files or len(files) < 2:
                continue  # Skip mass refactor noise or single-file commits

            sorted_files = sorted(list(files))
            for i in range(len(sorted_files)):
                for j in range(i + 1, len(sorted_files)):
                    pair = (sorted_files[i], sorted_files[j])
                    co_changes[pair] += 1

        # Step 3: Compute degree ratio = co_changes / min(commits(A), commits(B))
        results = []
        for (f_a, f_b), count in co_changes.items():
            min_commits = min(file_commit_counts[f_a], file_commit_counts[f_b])
            if min_commits == 0:
                continue

            degree = round(count / min_commits, 3)
            if degree >= threshold:
                results.append({
                    "file_a": f_a,
                    "file_b": f_b,
                    "co_changes": count,
                    "degree": degree,
                })

        results.sort(key=lambda x: (x["degree"], x["co_changes"]), reverse=True)
        return results[:100]

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
        hotspots = await get_repository_hotspots(repo_id, user, db)

        # Aggregate author commit totals across entire repository
        author_totals = defaultdict(int)
        orphan_files = []

        for h in hotspots:
            if h.is_deleted:
                continue

            for author in h.authors:
                author_totals[author] += 1

            if h.is_orphan_risk:
                orphan_files.append({
                    "file_path": h.file_path,
                    "commits_count": h.commits_count,
                    "top_author": h.top_author,
                    "top_author_share": h.top_author_share,
                })

        # Calculate Bus Factor: minimum number of authors accounting for >= 50% of total commits
        sorted_authors = sorted(author_totals.items(), key=lambda x: x[1], reverse=True)
        total_commits = sum(author_totals.values()) or 1

        cumulative = 0
        bus_factor = 0
        for _, count in sorted_authors:
            cumulative += count
            bus_factor += 1
            if cumulative >= (total_commits * 0.5):
                break

        return {
            "repo_bus_factor": max(bus_factor, 1),
            "top_contributors": dict(sorted_authors[:10]),
            "orphan_risk_files": orphan_files[:50],
        }

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
        hotspots = await get_repository_hotspots(repo_id, user, db)
        coupling = await get_temporal_coupling(repo_id, user, db)
        bus_factor_data = await get_bus_factor_analytics(repo_id, user, db)

        commit_types_dist = defaultdict(int)
        total_commits = 0
        orphan_count = 0

        for h in hotspots:
            if h.is_orphan_risk:
                orphan_count += 1
            for c_type, count in h.commit_types.items():
                commit_types_dist[c_type] += count
                total_commits += count

        return {
            "total_commits": total_commits,
            "total_files": len(hotspots),
            "bus_factor": bus_factor_data.repo_bus_factor,
            "commit_types_distribution": dict(commit_types_dist),
            "total_coupled_pairs": len(coupling),
            "orphan_files_count": orphan_count,
        }

    except Exception as exc:
        logger.error("Failed to compute summary for repo %s: %s", repo_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing summary analytics: {exc}",
        )

