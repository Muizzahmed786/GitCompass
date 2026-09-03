"""
Analytics service module.

Handles calculation of aggregated Git history analytics:
- Hotspots & Churn
- Temporal Coupling Co-Change Matrix
- Bus Factor & Knowledge Loss Index
- Analytics Overview Summary
"""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("gitcompass.services.analytics")

async def calculate_hotspots(
    db: Any,
    repo_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    commit_type: Optional[str] = None
) -> List[Dict[str, Any]]:
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


async def calculate_temporal_coupling(
    db: Any,
    repo_id: str,
    threshold: float,
    max_commit_files: int
) -> List[Dict[str, Any]]:
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


async def calculate_bus_factor(
    db: Any,
    repo_id: str
) -> Dict[str, Any]:
    hotspots = await calculate_hotspots(db, repo_id)

    # Aggregate author commit totals across entire repository
    author_totals = defaultdict(int)
    orphan_files = []

    for h in hotspots:
        if h["is_deleted"]:
            continue

        for author in h["authors"]:
            author_totals[author] += 1

        if h["is_orphan_risk"]:
            orphan_files.append({
                "file_path": h["file_path"],
                "commits_count": h["commits_count"],
                "top_author": h["top_author"],
                "top_author_share": h["top_author_share"],
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


async def calculate_summary(
    db: Any,
    repo_id: str
) -> Dict[str, Any]:
    hotspots = await calculate_hotspots(db, repo_id)
    # Using defaults for threshold and max_commit_files for summary
    coupling = await calculate_temporal_coupling(db, repo_id, threshold=0.5, max_commit_files=50)
    bus_factor_data = await calculate_bus_factor(db, repo_id)

    commit_types_dist = defaultdict(int)
    total_commits = 0
    orphan_count = 0

    for h in hotspots:
        if h["is_orphan_risk"]:
            orphan_count += 1
        for c_type, count in h["commit_types"].items():
            commit_types_dist[c_type] += count
            total_commits += count

    return {
        "total_commits": total_commits,
        "total_files": len(hotspots),
        "bus_factor": bus_factor_data["repo_bus_factor"],
        "commit_types_distribution": dict(commit_types_dist),
        "total_coupled_pairs": len(coupling),
        "orphan_files_count": orphan_count,
    }
