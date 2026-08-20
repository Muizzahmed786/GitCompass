import logging
import os
from datetime import datetime
from typing import List, Dict, Any

from app.database import get_service_client

logger = logging.getLogger("gitcompass.phase_analyzer")

PHASE_GAP_DAYS = 14

SIGNIFICANT_EVENT_TYPES = {
    "directory_introduced",
    "dependency_added",
    "dependency_removed",
    "dependency_version_changed",
    "manifest_introduced",
    "large_change",
    "commit_declared_refactor"
}

def is_significant_event(event: Dict[str, Any]) -> bool:
    """Filter to only include architectural/structural events."""
    return event.get("event_type") in SIGNIFICANT_EVENT_TYPES

def calculate_days_gap(date1: datetime, date2: datetime) -> float:
    return abs((date2 - date1).total_seconds()) / (60 * 60 * 24)

def cluster_events_into_phases(events: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Cluster events into phases if the time gap exceeds PHASE_GAP_DAYS."""
    if not events:
        return []

    # Ensure chronologically sorted
    sorted_events = sorted(events, key=lambda e: e["event_date"])
    
    phases = []
    current_phase = []
    last_date = None

    for event in sorted_events:
        if not is_significant_event(event):
            continue

        evt_date = event["event_date"]
        
        if last_date is None:
            current_phase.append(event)
        else:
            gap = calculate_days_gap(last_date, evt_date)
            if gap > PHASE_GAP_DAYS:
                # Start new phase
                phases.append(current_phase)
                current_phase = [event]
            else:
                current_phase.append(event)
                
        last_date = evt_date

    if current_phase:
        phases.append(current_phase)

    return phases

def generate_phase_title(phase_events: List[Dict[str, Any]], phase_index: int) -> str:
    """
    Deterministically generate a phase title based on evidence.
    Rules:
    1. Recognized framework/dependency
    2. Recognized architectural technology
    3. Dominant directory/module
    4. Dominant event type
    5. Generic phase title
    """
    event_counts = {}
    dep_counts = {}
    dir_counts = {}
    
    for evt in phase_events:
        e_type = evt["event_type"]
        event_counts[e_type] = event_counts.get(e_type, 0) + 1
        
        meta = evt.get("metadata", {})
        if "dependency" in meta:
            dep_counts[meta["dependency"]] = dep_counts.get(meta["dependency"], 0) + 1
            
        if "path" in meta:
            # path could be directory path or file path
            path = meta["path"]
            if e_type == "directory_introduced":
                dir_counts[path] = dir_counts.get(path, 0) + 1
            else:
                d = os.path.dirname(path)
                if d and d != ".":
                    dir_counts[d] = dir_counts.get(d, 0) + 1

    # 1 & 2: Recognized Frameworks/Tech
    # Sort deps deterministically by count desc, then alphabetically
    sorted_deps = sorted(dep_counts.items(), key=lambda x: (-x[1], x[0]))
    if sorted_deps:
        top_dep = sorted_deps[0][0].lower()
        if "react" in top_dep:
            return "React Frontend Foundation"
        if "fastapi" in top_dep:
            return "FastAPI Backend Foundation"
        if "express" in top_dep:
            return "Express Backend Setup"
        if "mongo" in top_dep or "mongoose" in top_dep:
            return "MongoDB Integration"
        if "postgres" in top_dep or "pg" in top_dep or "psycopg" in top_dep:
            return "PostgreSQL Integration"
        if "docker" in top_dep:
            return "Docker Infrastructure Setup"
        if "redis" in top_dep:
            return "Redis Integration"
        
        # Fallback to general dependency addition
        return f"{sorted_deps[0][0].title()} Integration"
        
    # 3: Dominant Directory
    sorted_dirs = sorted(dir_counts.items(), key=lambda x: (-x[1], x[0]))
    if sorted_dirs:
        top_dir = sorted_dirs[0][0].lower()
        if "server" in top_dir or "backend" in top_dir or "api" in top_dir:
            return "Backend Structure Expansion"
        if "client" in top_dir or "frontend" in top_dir or "ui" in top_dir:
            return "Frontend Structure Expansion"
        if "auth" in top_dir:
            return "Authentication Module Evolution"
            
        return f"Structure Expansion: {sorted_dirs[0][0]}"
        
    # 4: Dominant Event Type
    sorted_events = sorted(event_counts.items(), key=lambda x: (-x[1], x[0]))
    if sorted_events:
        top_event = sorted_events[0][0]
        if top_event == "large_change":
            return "Major Refactoring & Churn"
        if top_event == "commit_declared_refactor":
            return "Focused Refactoring Phase"
        if top_event == "manifest_introduced":
            return "New Subproject or Module Initialization"
            
    # 5: Generic Phase Title
    return f"Repository Evolution Phase {phase_index}"

def calculate_phase_metadata(phase_events: List[Dict[str, Any]], phase_index: int) -> Dict[str, Any]:
    event_counts = {}
    for evt in phase_events:
        e_type = evt["event_type"]
        event_counts[e_type] = event_counts.get(e_type, 0) + 1
        
    sorted_events = sorted(event_counts.items(), key=lambda x: (-x[1], x[0]))
    dominant = sorted_events[0][0] if sorted_events else None
    
    start_date = phase_events[0]["event_date"] if phase_events else None
    end_date = phase_events[-1]["event_date"] if phase_events else None
    
    title = generate_phase_title(phase_events, phase_index)
    
    return {
        "phase_index": phase_index,
        "start_date": start_date,
        "end_date": end_date,
        "title": title,
        "dominant_event_type": dominant,
        "event_count": len(phase_events)
    }

def analyze_phases(repo_id: str):
    """
    Main entry point for Stage 6.
    Loads repository events, clusters them into phases, calculates metadata,
    and persists them to the database idempotently.
    """
    logger.info("[Stage 6] Starting phase analysis for repo %s", repo_id)
    db = get_service_client()
    
    try:
        # 1. Load repository events
        logger.info("[Stage 6] Loading repository events")
        res = db.table("repository_events").select("*").eq("repo_id", repo_id).order("event_date", desc=False).execute()
        events = res.data or []
        
        # Convert string dates to datetime for sorting and clustering
        for evt in events:
            if isinstance(evt["event_date"], str):
                evt["event_date"] = datetime.fromisoformat(evt["event_date"].replace('Z', '+00:00'))
                
        # Filter significant events
        sig_events = [e for e in events if is_significant_event(e)]
        logger.info("[Stage 6] Significant events: %d", len(sig_events))
        
        if not sig_events:
            logger.info("[Stage 6] No significant events found. Removing old phases and exiting.")
            db.table("architecture_phases").delete().eq("repo_id", repo_id).execute()
            return
            
        # 2. Cluster events into phases
        phase_clusters = cluster_events_into_phases(sig_events)
        logger.info("[Stage 6] Identified phases: %d", len(phase_clusters))
        
        # 3. Clean up existing phases for this repo (Idempotency)
        db.table("architecture_phases").delete().eq("repo_id", repo_id).execute()
        
        # 4. Process and persist each phase
        logger.info("[Stage 6] Persisting architecture phases")
        
        for idx, phase_events in enumerate(phase_clusters, start=1):
            metadata = calculate_phase_metadata(phase_events, idx)
            
            # Insert phase
            phase_insert = db.table("architecture_phases").insert({
                "repo_id": repo_id,
                "phase_index": metadata["phase_index"],
                "start_date": metadata["start_date"].isoformat(),
                "end_date": metadata["end_date"].isoformat(),
                "title": metadata["title"],
                "dominant_event_type": metadata["dominant_event_type"],
                "event_count": metadata["event_count"]
            }).execute()
            
            if phase_insert.data:
                phase_id = phase_insert.data[0]["id"]
                
                # Map events to this phase
                phase_events_data = [
                    {"phase_id": phase_id, "event_id": evt["id"]} 
                    for evt in phase_events
                ]
                
                if phase_events_data:
                    # Supabase insert limit is usually high enough for ~1000 records, but let's be safe.
                    # Typical architectural phases are < 50 events.
                    db.table("architecture_phase_events").insert(phase_events_data).execute()
                    
        logger.info("[Stage 6] Phase analysis complete")
    except Exception as e:
        logger.error("[Stage 6] Phase analysis failed for repo %s: %s", repo_id, str(e), exc_info=True)
        raise
