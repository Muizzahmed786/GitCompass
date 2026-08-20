"""
AI Router — Exposes endpoints for Gemini AI intelligence.
"""

import logging
from collections import defaultdict
from enum import Enum
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.dependencies import CurrentUser, UserDB
from app.services.ai_service import (
    generate_evolution_summary,
    detect_architecture_shifts,
    answer_qa,
    generate_development_story,
)
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
    summary: str | None = None
    is_cached: bool = False
    is_stale: bool = False

class ChatRequest(BaseModel):
    question: str

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
            aggregated_data=aggregated_data,
            selected_model=selected_model
        )
        
        # Save to cache
        db.table("ai_analysis_cache").upsert({
            "repo_id": repo_id,
            "analysis_type": "summary",
            "model": selected_model,
            "latest_sha": latest_sha,
            "content": summary_text
        }, on_conflict="repo_id,analysis_type,model").execute()

        return {"summary": summary_text}

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

        # Fetch deterministic phases and their evidence (Stage 6 -> Stage 7)
        phases_res = (
            db.table("architecture_phases")
            .select("id, title, start_date, end_date, dominant_event_type")
            .eq("repo_id", repo_id)
            .order("start_date", desc=False)
            .execute()
        )
        
        phases = []
        for phase_row in (phases_res.data or []):
            phase_id = phase_row["id"]
            
            # Fetch events for this phase
            # Supabase Python client doesn't support deep nested joins easily, so we can fetch all events and filter, or fetch per phase.
            # Let's fetch the event data using a join
            events_res = (
                db.table("architecture_phase_events")
                .select("event_id, repository_events(event_type, event_key, event_date, metadata)")
                .eq("phase_id", phase_id)
                .execute()
            )
            
            evidence = []
            for ev_row in (events_res.data or []):
                evt = ev_row.get("repository_events")
                if evt:
                    evidence.append({
                        "type": evt.get("event_type"),
                        "name": evt.get("event_key"),
                        "date": evt.get("event_date"),
                        "metadata": evt.get("metadata")
                    })
            
            phases.append({
                "phase": {
                    "title": phase_row["title"],
                    "start_date": phase_row["start_date"],
                    "end_date": phase_row["end_date"],
                    "dominant_event_type": phase_row["dominant_event_type"]
                },
                "evidence": evidence
            })

        shifts = await detect_architecture_shifts(
            repo_name=repo_name,
            total_commits=total_commits,
            structured_phases=phases,
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

        # Fetch commits chronologically
        commits_res = (
            db.table("commits")
            .select("id, committed_at, message, insertions, deletions")
            .eq("repo_id", repo_id)
            .order("committed_at", desc=False)
            .limit(500)
            .execute()
        )

        commits = commits_res.data or []
        if len(commits) < 3:
            return {"story": "The available repository history is insufficient to establish a clear story."}

        # Group by month YYYY-MM
        monthly_groups = defaultdict(lambda: {
            "commit_count": 0,
            "additions": 0,
            "deletions": 0,
            "messages": []
        })

        for c in commits:
            dt_str = c.get("committed_at", "")[:7] or "Unknown"
            grp = monthly_groups[dt_str]
            grp["commit_count"] += 1
            grp["additions"] += c.get("insertions") or 0
            grp["deletions"] += c.get("deletions") or 0
            msg = (c.get("message") or "").strip().split("\n")[0]
            if msg and len(msg) > 5 and msg not in grp["messages"]:
                grp["messages"].append(msg)

        # Build timeline periods list
        timeline_periods = []
        for period, data in sorted(monthly_groups.items(), key=lambda x: x[0]):
            timeline_periods.append({
                "period": period,
                "commit_count": data["commit_count"],
                "total_insertions": data["additions"],
                "total_deletions": data["deletions"],
                "sample_messages": data["messages"][:4]  # max 4 sample messages per month
            })

        # Compress older months if history spans more than 12 periods
        if len(timeline_periods) > 12:
            compressed = []
            chunk_size = (len(timeline_periods) + 11) // 12
            for i in range(0, len(timeline_periods), chunk_size):
                chunk = timeline_periods[i:i + chunk_size]
                start_p = chunk[0]["period"]
                end_p = chunk[-1]["period"]
                label = start_p if start_p == end_p else f"{start_p} to {end_p}"
                c_count = sum(x["commit_count"] for x in chunk)
                ins = sum(x["total_insertions"] for x in chunk)
                dels = sum(x["total_deletions"] for x in chunk)
                msgs = []
                for x in chunk:
                    msgs.extend(x["sample_messages"])
                compressed.append({
                    "period": label,
                    "commit_count": c_count,
                    "total_insertions": ins,
                    "total_deletions": dels,
                    "sample_messages": msgs[:5]
                })
            timeline_periods = compressed

        story_text = await generate_development_story(
            repo_name=repo_name,
            timeline_data={"periods": timeline_periods},
            selected_model=selected_model
        )
        
        # Save to cache
        db.table("ai_analysis_cache").upsert({
            "repo_id": repo_id,
            "analysis_type": "story",
            "model": selected_model,
            "latest_sha": latest_sha,
            "content": story_text
        }, on_conflict="repo_id,analysis_type,model").execute()

        return {"story": story_text}

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Development story failed for repo %s: %s", repo_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Development story generation failed: {exc}")


