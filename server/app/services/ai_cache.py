"""
AI Cache Service.

Provides reusable caching logic for AI endpoints.
"""

from typing import Any, Dict, Optional, Tuple

def check_cache(
    db: Any,
    repo_id: str,
    analysis_type: str,
    selected_model: str,
    latest_sha: str,
    force_refresh: bool
) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Checks if a valid cached AI response exists.
    Returns (should_use_cache, cached_response_dict)
    """
    if force_refresh:
        return False, None

    cache_res = db.table("ai_analysis_cache").select("content, latest_sha").eq("repo_id", repo_id).eq("analysis_type", analysis_type).eq("model", selected_model).execute()
    
    if not cache_res.data:
        return True, {analysis_type: None, "is_cached": False, "is_stale": False}
    
    cached_content = cache_res.data[0]["content"]
    is_stale = (cache_res.data[0].get("latest_sha") != latest_sha)
    
    return True, {analysis_type: cached_content, "is_cached": True, "is_stale": is_stale}


def save_cache(
    db: Any,
    repo_id: str,
    analysis_type: str,
    selected_model: str,
    latest_sha: str,
    content: Any
):
    """Saves the generated AI response to the cache."""
    db.table("ai_analysis_cache").upsert({
        "repo_id": repo_id,
        "analysis_type": analysis_type,
        "model": selected_model,
        "latest_sha": latest_sha,
        "content": content
    }, on_conflict="repo_id,analysis_type,model").execute()
