"""
Extractor service module.

Parses Git history using high-performance bulk log streaming (`git log --numstat -M`).
Handles commit metadata, per-file diff stats, and file renames.
"""

from datetime import datetime, timezone
import logging
import re
import subprocess
import uuid
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("gitcompass.extractor")

RENAME_PATTERN_BRACES = re.compile(r"^(.*?)\{(.*?) => (.*?)\}(.*)$")
RENAME_PATTERN_SIMPLE = re.compile(r"^(.*?) => (.*)$")
CONVENTIONAL_COMMIT_PATTERN = re.compile(
    r"^(feat|fix|refactor|docs|test|chore|perf|style|ci|build|revert)(?:\([^\)]+\))?!?:\s*",
    re.IGNORECASE,
)


def classify_commit_type(message: str) -> str:
    """Classifies commit message into standard Conventional Commit types.

    Returns one of: 'feat', 'fix', 'refactor', 'docs', 'test', 'chore', 'perf', 'style', 'ci', 'build', 'revert', or 'other'.
    """
    if not message:
        return "other"

    msg = message.strip()
    match = CONVENTIONAL_COMMIT_PATTERN.match(msg)
    if match:
        return match.group(1).lower()

    # Fallback heuristic checking leading words or prefix
    lower_msg = msg.lower()
    for ctype in ["feat", "fix", "refactor", "docs", "test", "chore", "perf", "style", "ci", "build", "revert"]:
        if lower_msg.startswith(f"{ctype}:") or lower_msg.startswith(f"{ctype} "):
            return ctype

    return "other"


def parse_git_path(path_str: str) -> Tuple[str, Optional[str], bool]:
    """Parses Git numstat file path into (current_path, old_path, is_rename).

    Examples:
        "src/app.py" -> ("src/app.py", None, False)
        "old.py => new.py" -> ("new.py", "old.py", True)
        "src/{old => new}/utils.py" -> ("src/new/utils.py", "src/old/utils.py", True)
    """
    path_str = path_str.strip()

    # Case 1: Braced rename `prefix/{old => new}/suffix`
    m_brace = RENAME_PATTERN_BRACES.match(path_str)
    if m_brace:
        prefix, old_mid, new_mid, suffix = m_brace.groups()
        old_path = (prefix + old_mid + suffix).replace("//", "/")
        new_path = (prefix + new_mid + suffix).replace("//", "/")
        return new_path, old_path, True

    # Case 2: Simple rename `old => new`
    m_simple = RENAME_PATTERN_SIMPLE.match(path_str)
    if m_simple:
        old_path = m_simple.group(1).strip()
        new_path = m_simple.group(2).strip()
        return new_path, old_path, True

    # Case 3: Regular file path
    return path_str, None, False


def extract_git_history(
    repo_dir: str, repo_id: str, user_id: str, since_sha: Optional[str] = None, progress_callback=None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int, int, Optional[str]]:
    """Bulk parses Git history for a repository.

    Returns:
        (commits_list, file_diffs_list, total_commits, total_files, latest_commit_sha)
    """
    logger.info("Extracting Git history for repo %s from %s (since_sha=%s)", repo_id, repo_dir, since_sha)

    log_range = f"{since_sha}..HEAD" if since_sha else "HEAD"

    # Pre-flight check: total expected commits
    total_commits_expected = 0
    try:
        count_proc = subprocess.run(
            ["git", "rev-list", "--count", log_range],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=30,
        )
        if count_proc.returncode == 0:
            total_commits_expected = int(count_proc.stdout.strip())
            logger.info("Pre-flight check: Expecting %d commits for %s", total_commits_expected, repo_id)
    except Exception as exc:
        logger.warning("Failed to count expected commits: %s", exc)

    # Bulk git log command with --numstat and rename detection (-M)
    cmd = [
        "git",
        "log",
        "--numstat",
        "--format=COMMIT:%H|%an|%ae|%at|%s",
        "-M",
        log_range,
    ]

    try:
        proc = subprocess.Popen(
            cmd,
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            errors="replace"
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to start git log process: {exc}")

    commits: List[Dict[str, Any]] = []
    file_diffs: List[Dict[str, Any]] = []
    unique_files: set[str] = set()
    rename_map: Dict[str, str] = {}

    current_commit: Optional[Dict[str, Any]] = None
    commit_insertions = 0
    commit_deletions = 0
    
    commits_processed = 0
    last_reported_pct = 0

    try:
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue

            if line.startswith("COMMIT:"):
                # Finalize previous commit stats before starting new one
                if current_commit:
                    current_commit["insertions"] = commit_insertions
                    current_commit["deletions"] = commit_deletions
                    commits.append(current_commit)
                    
                    commits_processed += 1
                    
                    if progress_callback and total_commits_expected > 0:
                        current_pct = int((commits_processed / total_commits_expected) * 100)
                        if current_pct > last_reported_pct:
                            progress_callback(current_pct)
                            last_reported_pct = current_pct

                # Reset per-commit trackers
                commit_insertions = 0
                commit_deletions = 0

                # Parse line format: COMMIT:sha|author_name|author_email|timestamp|message
                raw_data = line[7:]
                parts = raw_data.split("|", 4)

                sha = parts[0] if len(parts) > 0 else ""
                author_name = parts[1] if len(parts) > 1 else ""
                author_email = parts[2] if len(parts) > 2 else ""
                raw_ts = parts[3] if len(parts) > 3 else "0"
                message = parts[4] if len(parts) > 4 else ""

                try:
                    ts_int = int(raw_ts)
                    committed_at = datetime.fromtimestamp(ts_int, tz=timezone.utc).isoformat()
                except ValueError:
                    committed_at = datetime.now(timezone.utc).isoformat()

                commit_id = str(uuid.uuid4())
                current_commit = {
                    "id": commit_id,
                    "repo_id": repo_id,
                    "user_id": user_id,
                    "sha": sha,
                    "author_name": author_name,
                    "author_email": author_email,
                    "committed_at": committed_at,
                    "message": message,
                    "commit_type": classify_commit_type(message),
                    "insertions": 0,
                    "deletions": 0,
                }
            elif current_commit:
                # Numstat line: <insertions>\t<deletions>\t<path>
                parts = line.split("\t", 2)
                if len(parts) == 3:
                    raw_ins, raw_del, raw_path = parts[0], parts[1], parts[2]

                    # Handle binary files ("-  -   file.png")
                    ins = int(raw_ins) if raw_ins.isdigit() else 0
                    dels = int(raw_del) if raw_del.isdigit() else 0

                    current_path, old_path, is_rename = parse_git_path(raw_path)
                    
                    # Because git log outputs newest -> oldest, we can trace renames backwards.
                    # If we see a rename, map the old name to whatever the new name ultimately maps to.
                    if is_rename and old_path:
                        target = rename_map.get(current_path, current_path)
                        rename_map[old_path] = target
                    
                    # Resolve the current path to its most modern name
                    actual_path = rename_map.get(current_path, current_path)
                    
                    unique_files.add(actual_path)

                    commit_insertions += ins
                    commit_deletions += dels

                    file_diffs.append(
                        {
                            "id": str(uuid.uuid4()),
                            "commit_id": current_commit["id"],
                            "repo_id": repo_id,
                            "user_id": user_id,
                            "file_path": actual_path,
                            "old_path": old_path,
                            "is_rename": is_rename,
                            "insertions": ins,
                            "deletions": dels,
                        }
                    )

        # Don't forget the last commit
        if current_commit:
            current_commit["insertions"] = commit_insertions
            current_commit["deletions"] = commit_deletions
            commits.append(current_commit)

        # Wait for the process to finish
        proc.wait()
        if proc.returncode != 0:
            logger.warning(f"Git log finished with non-zero exit code: {proc.returncode}")

    finally:
        # Cleanup orphan process if exception occurs mid-stream
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        
        # Close stdout to prevent ResourceWarning
        if proc.stdout:
            proc.stdout.close()

    # Filter out files that no longer exist in HEAD (deleted files)
    active_files: set[str] = set()
    try:
        ls_proc = subprocess.run(
            ["git", "ls-tree", "-r", "HEAD", "--name-only"],
            cwd=repo_dir,
            stdout=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=30,
        )
        if ls_proc.returncode == 0:
            active_files = set(ls_proc.stdout.splitlines())
    except Exception as exc:
        logger.warning("Failed to run git ls-tree: %s", exc)

    if active_files:
        # Find files that are in unique_files but NOT in active_files (deleted files)
        deleted_files = unique_files - active_files
        
        # Tag deleted files in file_diffs rather than removing them
        for fd in file_diffs:
            if fd["file_path"] in deleted_files:
                fd["is_deleted"] = True
            else:
                fd["is_deleted"] = False
    else:
        # If we failed to get active_files or repo is completely empty, assume active
        for fd in file_diffs:
            fd["is_deleted"] = False

    # Handle Gitignore rules natively
    ignored_files: set[str] = set()
    if unique_files:
        try:
            # We cloned with --no-checkout to save I/O and space, which means .gitignore files 
            # are not on disk. We must explicitly extract them before running check-ignore.
            checkout_cmd = "git ls-tree -r HEAD --name-only | grep '\\.gitignore$' | xargs -I {} git checkout HEAD -- {}"
            subprocess.run(checkout_cmd, shell=True, cwd=repo_dir, stderr=subprocess.PIPE, stdout=subprocess.PIPE)

            # check-ignore --no-index --stdin accepts paths and returns the ones that match .gitignore
            # --no-index is crucial: without it, tracked files are NOT ignored even if in .gitignore!
            ignore_proc = subprocess.run(
                ["git", "check-ignore", "--no-index", "--stdin"],
                input="\n".join(unique_files),
                cwd=repo_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                timeout=30,
            )
            if ignore_proc.returncode in (0, 1): # 0 means some matched, 1 means none matched
                ignored_files = set(ignore_proc.stdout.splitlines())
        except Exception as exc:
            logger.warning("Failed to run git check-ignore: %s", exc)

    if ignored_files:
        # Filter out file diffs that match ignored files
        file_diffs = [fd for fd in file_diffs if fd["file_path"] not in ignored_files]
        unique_files = unique_files - ignored_files

    latest_commit_sha = commits[0]["sha"] if commits else None

    logger.info(
        "Extracted %d commits and %d file diffs across %d unique files for repo %s (latest_sha=%s)",
        len(commits),
        len(file_diffs),
        len(unique_files),
        repo_id,
        latest_commit_sha,
    )

    return commits, file_diffs, len(commits), len(unique_files), latest_commit_sha
