"""
Chat retrieval service.

Handles extracting paths from chat history and assembling specific evidence slices.
"""

import re
from typing import Any, Dict, List, Set, Tuple, Optional
from app.services.evidence_assembler import retrieve_repository_slice

def resolve_chat_evidence(
    db: Any,
    repo_id: str,
    evidence: Dict[str, Any],
    history: List[Any],
    page_context: Optional[Dict[str, Any]]
) -> Tuple[Optional[Dict[str, Any]], Set[str]]:
    """
    Identifies target files from context and conversation history.
    Retrieves the specific slice for that file.
    Returns (specific_slice, supplied_paths_set)
    """
    specific_slice = None
    target_path = None
    supplied_paths = set()
    
    # Collect paths from general hotspots
    if evidence.get("hotspots"):
        for hs in evidence["hotspots"]:
            if hs.get("file_path"):
                supplied_paths.add(hs["file_path"])

    # 1. From page_context
    if page_context and page_context.get("selected_file"):
        target_path = page_context.get("selected_file")
    
    # 2. From regex in the latest question
    if not target_path and history:
        latest_msg = history[-1].content
        matches = re.findall(r'([a-zA-Z0-9_\-\./]+(?:/[a-zA-Z0-9_\-\.]+)+\.[a-zA-Z0-9]+)', latest_msg)
        if matches:
            target_path = matches[0]

    if target_path:
        # Normalize and validate path
        target_path = target_path.strip().lstrip('/')
        if '..' not in target_path:
            specific_slice = retrieve_repository_slice(repo_id, target_path, db)
            if specific_slice:
                supplied_paths.add(specific_slice["path"])
                
    return specific_slice, supplied_paths
