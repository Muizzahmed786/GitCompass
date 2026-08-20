import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.database import get_service_client
from app.services.dependency_analyzer import (
    parse_package_json, parse_requirements_txt, parse_pyproject_toml,
    parse_pom_xml, parse_docker_compose
)

logger = logging.getLogger("gitcompass.evolution_analyzer")

# Recognized manifest files based on Stage 1/2
MANIFEST_PATTERNS = {
    "package.json": parse_package_json,
    "requirements.txt": parse_requirements_txt,
    "pyproject.toml": parse_pyproject_toml,
    "pom.xml": parse_pom_xml,
    "docker-compose.yml": parse_docker_compose,
    "docker-compose.yaml": parse_docker_compose,
}

def get_commit_parents(repo_dir: str, sha: str) -> List[str]:
    """Retrieve parent SHAs for a given commit."""
    try:
        proc = subprocess.run(
            ["git", "log", "--format=%P", "-n", "1", sha],
            cwd=repo_dir, capture_output=True, text=True, check=True
        )
        parents = proc.stdout.strip().split()
        return parents
    except subprocess.CalledProcessError:
        return []

def get_file_content_at_commit(repo_dir: str, sha: str, file_path: str) -> Optional[str]:
    """Retrieve file content at a specific commit using git show."""
    try:
        proc = subprocess.run(
            ["git", "show", f"{sha}:{file_path}"],
            cwd=repo_dir, capture_output=True, text=True, errors="replace"
        )
        if proc.returncode == 0:
            return proc.stdout
        return None
    except Exception:
        return None

def directory_exists_at_commit(repo_dir: str, sha: str, dir_path: str) -> bool:
    """Check if a directory existed in the repository at a given commit."""
    if not sha:
        return False
    try:
        proc = subprocess.run(
            ["git", "ls-tree", "-d", sha, dir_path],
            cwd=repo_dir, capture_output=True, text=True, errors="replace"
        )
        return bool(proc.stdout.strip())
    except Exception:
        return False

def analyze_dependencies_for_commit(repo_dir: str, commit: Dict[str, Any], file_diffs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Compare manifests against the first parent to detect dependency changes."""
    events = []
    sha = commit["sha"]
    parents = get_commit_parents(repo_dir, sha)
    
    # Deterministic merge handling: always compare against the first parent.
    # If no parents (initial commit), compare against empty.
    parent_sha = parents[0] if parents else None

    for diff in file_diffs:
        file_path = diff["file_path"]
        filename = Path(file_path).name.lower()
        
        if filename in MANIFEST_PATTERNS:
            parser_func = MANIFEST_PATTERNS[filename]
            
            after_content = get_file_content_at_commit(repo_dir, sha, file_path)
            after_deps = parser_func(after_content, file_path) if after_content else []
            after_map = {d.name: d.version for d in after_deps}
            
            before_deps = []
            if parent_sha:
                old_path = diff.get("old_path") or file_path
                before_content = get_file_content_at_commit(repo_dir, parent_sha, old_path)
                before_deps = parser_func(before_content, old_path) if before_content else []
            before_map = {d.name: d.version for d in before_deps}
            
            # Detect Added / Version Changed
            for name, after_v in after_map.items():
                if name not in before_map:
                    events.append({
                        "event_type": "dependency_added",
                        "event_key": f"dependency:{file_path}:{name}",
                        "description": f"Added dependency {name} ({after_v}) in {file_path}",
                        "metadata": {
                            "manifest": file_path,
                            "dependency": name,
                            "before_version": None,
                            "after_version": after_v
                        }
                    })
                elif before_map[name] != after_v:
                    events.append({
                        "event_type": "dependency_version_changed",
                        "event_key": f"dependency:{file_path}:{name}",
                        "description": f"Changed dependency {name} version from {before_map[name]} to {after_v} in {file_path}",
                        "metadata": {
                            "manifest": file_path,
                            "dependency": name,
                            "before_version": before_map[name],
                            "after_version": after_v
                        }
                    })
            
            # Detect Removed
            for name, before_v in before_map.items():
                if name not in after_map:
                    events.append({
                        "event_type": "dependency_removed",
                        "event_key": f"dependency:{file_path}:{name}",
                        "description": f"Removed dependency {name} ({before_v}) from {file_path}",
                        "metadata": {
                            "manifest": file_path,
                            "dependency": name,
                            "before_version": before_v,
                            "after_version": None
                        }
                    })
                    
    return events


def analyze_evolution(repo_id: str, temp_dir: str, commits: List[Dict[str, Any]], file_diffs: List[Dict[str, Any]]):
    """
    Analyzes historical commits to detect deterministic architectural events.
    """
    logger.info("Starting evolution analysis for repo %s with %d commits", repo_id, len(commits))
    if not commits:
        return

    events = []
    
    # Group diffs by commit
    diffs_by_commit = {}
    for fd in file_diffs:
        diffs_by_commit.setdefault(fd["commit_id"], []).append(fd)
        
    seen_directories = set()
    seen_manifests = set()
    
    # We must process chronologically (oldest to newest) to correctly track introductions.
    chronological_commits = list(reversed(commits))
    
    # Calculate churn threshold for "large_change"
    total_churns = [(c["insertions"] + c["deletions"]) for c in chronological_commits]
    if len(total_churns) > 1:
        avg_churn = sum(total_churns) / len(total_churns)
        variance = sum((x - avg_churn) ** 2 for x in total_churns) / len(total_churns)
        std_dev = variance ** 0.5
        large_change_threshold = int(avg_churn + 2 * std_dev)
        large_change_threshold = max(large_change_threshold, 500)
    else:
        large_change_threshold = 500

    for commit in chronological_commits:
        commit_id = commit["id"]
        sha = commit["sha"]
        c_date = commit["committed_at"]
        msg = commit["message"]
        
        diffs = diffs_by_commit.get(commit_id, [])
        
        # 1. Dependency Changes
        dep_events = analyze_dependencies_for_commit(temp_dir, commit, diffs)
        for de in dep_events:
            events.append({
                "repo_id": repo_id,
                "commit_id": commit_id,
                "event_type": de["event_type"],
                "event_key": de["event_key"],
                "description": de["description"],
                "event_date": c_date,
                "metadata": de["metadata"]
            })
            
        # 2. Structural Introductions
        introduced_dirs = {}
        for diff in diffs:
            file_path = diff["file_path"]
            filename = Path(file_path).name.lower()
            
            # Manifests
            if filename in MANIFEST_PATTERNS and file_path not in seen_manifests:
                seen_manifests.add(file_path)
                events.append({
                    "repo_id": repo_id,
                    "commit_id": commit_id,
                    "event_type": "manifest_introduced",
                    "event_key": f"manifest:{file_path}",
                    "description": f"Introduced manifest {file_path}",
                    "event_date": c_date,
                    "metadata": {"path": file_path}
                })
            
            # Directories (Highest meaningful directory)
            dir_path = str(Path(file_path).parent).replace('\\', '/')
            if dir_path != "." and dir_path not in seen_directories:
                introduced_dirs.setdefault(dir_path, []).append(file_path)

        for dir_path, files in introduced_dirs.items():
            if dir_path not in seen_directories:
                parents = get_commit_parents(temp_dir, sha)
                parent_sha = parents[0] if parents else None
                
                # If it already existed before this commit (e.g. crossing incremental sync boundary)
                if parent_sha and directory_exists_at_commit(temp_dir, parent_sha, dir_path):
                    seen_directories.add(dir_path)
                    parent = Path(dir_path).parent
                    while str(parent) != ".":
                        seen_directories.add(str(parent).replace('\\', '/'))
                        parent = parent.parent
                    continue

                seen_directories.add(dir_path)
                parent = Path(dir_path).parent
                while str(parent) != ".":
                    seen_directories.add(str(parent).replace('\\', '/'))
                    parent = parent.parent
                    
                events.append({
                    "repo_id": repo_id,
                    "commit_id": commit_id,
                    "event_type": "directory_introduced",
                    "event_key": f"directory:{dir_path}",
                    "description": f"Introduced directory {dir_path}",
                    "event_date": c_date,
                    "metadata": {
                        "directory_path": dir_path,
                        "files_added": files
                    }
                })

        # 3. Large Change
        total_churn = commit["insertions"] + commit["deletions"]
        if total_churn > large_change_threshold:
            events.append({
                "repo_id": repo_id,
                "commit_id": commit_id,
                "event_type": "large_change",
                "event_key": f"large_change:{commit_id}",
                "description": f"Large commit with {total_churn} lines changed",
                "event_date": c_date,
                "metadata": {
                    "insertions": commit["insertions"],
                    "deletions": commit["deletions"],
                    "total_churn": total_churn,
                    "threshold": large_change_threshold
                }
            })
            
        # 4. Commit Declared Refactor
        if msg and (msg.lower().startswith("refactor:") or msg.lower().startswith("refactor(")):
            events.append({
                "repo_id": repo_id,
                "commit_id": commit_id,
                "event_type": "commit_declared_refactor",
                "event_key": f"refactor:{commit_id}",
                "description": "Commit message declares a refactor",
                "event_date": c_date,
                "metadata": {
                    "commit_message": msg
                }
            })
            
    # Batch insert events
    if events:
        db = get_service_client()
        logger.info("Writing %d evolution events for repo %s", len(events), repo_id)
        BATCH_SIZE = 500
        for i in range(0, len(events), BATCH_SIZE):
            chunk = events[i : i + BATCH_SIZE]
            db.table("repository_events").upsert(
                chunk, 
                on_conflict="repo_id,commit_id,event_type,event_key"
            ).execute()

    logger.info("Finished evolution analysis for repo %s", repo_id)
