"""
AI Router — Exposes endpoints for Gemini AI intelligence.
"""

import logging
from collections import defaultdict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dependencies import CurrentUser, UserDB
from app.services.ai_service import generate_evolution_summary, detect_architecture_shifts, answer_qa

logger = logging.getLogger("gitcompass.routers.ai")

router = APIRouter(prefix="/api/ai", tags=["ai"])


class AISummaryResponse(BaseModel):
    summary: str

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    answer: str


@router.post("/summary/{repo_id}", response_model=AISummaryResponse)
async def get_ai_summary(repo_id: str, user: CurrentUser, db: UserDB):
    """Generates AI summary of repository evolution using Gemini."""
    try:
        repo_res = db.table("repositories").select("name, total_commits").eq("id", repo_id).execute()
        if not repo_res.data:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_name = repo_res.data[0].get("name") or "Unknown"
        total_commits = repo_res.data[0].get("total_commits", 0)

        # Fetch file diffs joined with commits for hotspot aggregation
        hotspots_raw = (
            db.table("file_diffs")
            .select("file_path, insertions, deletions, commits!inner(author_name)")
            .eq("repo_id", repo_id)
            .limit(2000)
            .execute()
        )

        file_stats = defaultdict(lambda: {"commits_count": 0, "insertions": 0, "deletions": 0, "authors": defaultdict(int)})
        for row in (hotspots_raw.data or []):
            path = row["file_path"]
            author = (row.get("commits") or {}).get("author_name", "Unknown")
            file_stats[path]["commits_count"] += 1
            file_stats[path]["insertions"] += row.get("insertions", 0)
            file_stats[path]["deletions"] += row.get("deletions", 0)
            file_stats[path]["authors"][author] += 1

        hotspots = []
        for path, stats in sorted(file_stats.items(), key=lambda x: x[1]["commits_count"], reverse=True)[:10]:
            top_author = max(stats["authors"], key=stats["authors"].get) if stats["authors"] else "Unknown"
            hotspots.append({
                "file_path": path,
                "commits_count": stats["commits_count"],
                "insertions": stats["insertions"],
                "deletions": stats["deletions"],
                "top_author": top_author
            })

        # Count unique authors and commits per author
        authors_res = db.table("commits").select("author_name").eq("repo_id", repo_id).execute()
        author_counts = defaultdict(int)
        for r in (authors_res.data or []):
            if r.get("author_name"):
                author_counts[r["author_name"]] += 1
        
        bus_factor = max(len(author_counts), 1)
        top_authors = [{"author": k, "commits": v} for k, v in sorted(author_counts.items(), key=lambda x: x[1], reverse=True)[:5]]

        aggregated_data = {
            "repository": {
                "name": repo_name,
                "total_commits": total_commits,
                "total_files_changed": len(file_stats),
            },
            "contributors": {
                "total_count": len(author_counts),
                "bus_factor": bus_factor,
                "top_authors": top_authors
            },
            "hotspots": hotspots
        }

        summary_text = await generate_evolution_summary(
            repo_name=repo_name,
            aggregated_data=aggregated_data
        )
        return {"summary": summary_text}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("AI summary failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI summary generation failed: {exc}")


@router.post("/shifts/{repo_id}")
async def get_architecture_shifts(repo_id: str, user: CurrentUser, db: UserDB):
    """Detects architecture shifts using Gemini. Limited to repos with <= MAX_COMMITS."""
    try:
        repo_res = db.table("repositories").select("name, total_commits").eq("id", repo_id).execute()
        if not repo_res.data:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_name = repo_res.data[0].get("name") or "Unknown"
        total_commits = repo_res.data[0].get("total_commits") or 0

        # Fetch all commits ordered chronologically — no dependency on summary
        commits_res = (
            db.table("commits")
            .select("author_name, committed_at, message")
            .eq("repo_id", repo_id)
            .order("committed_at", desc=False)
            .limit(200)
            .execute()
        )

        shifts = await detect_architecture_shifts(
            repo_name=repo_name,
            total_commits=total_commits,
            significant_commits=commits_res.data or []
        )
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
    """Answers Q&A questions about the repository (Ephemeral, not cached)."""
    try:
        repo_res = db.table("repositories").select("name, total_commits").eq("id", repo_id).execute()
        if not repo_res.data:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_name = repo_res.data[0].get("name") or "Unknown"
        total_commits = repo_res.data[0].get("total_commits", 0)

        # Build context from top files
        hotspots_raw = (
            db.table("file_diffs")
            .select("file_path")
            .eq("repo_id", repo_id)
            .limit(1000)
            .execute()
        )

        file_counts = defaultdict(int)
        for row in (hotspots_raw.data or []):
            file_counts[row["file_path"]] += 1

        top_files = sorted(file_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        context = f"Repository: '{repo_name}', {total_commits} total commits\n"
        context += "Most frequently changed files:\n"
        context += "\n".join(f"- {f} ({c} commits)" for f, c in top_files)

        answer_text = await answer_qa(repo_name, payload.question, context)
        return {"answer": answer_text}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("AI chat failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI chat failed: {exc}")
