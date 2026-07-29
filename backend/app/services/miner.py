"""
Miner service module.

Orchestrates the background repository mining workflow:
1. Updates status (pending -> cloning -> mining -> ready / error)
2. Clones repository to isolated temporary directory
3. Bulk extracts commits and file diff statistics
4. Batch writes raw git data to Supabase using service-role client
5. Enforces guaranteed teardown of temporary clone folders
"""

from datetime import datetime, timezone
import logging
import tempfile
import tempfile
import traceback
from typing import List, Any, Optional

from app.database import get_service_client
from app.services.cloner import clone_repository, parse_github_url, safe_cleanup_dir
from app.services.extractor import extract_git_history

logger = logging.getLogger("gitcompass.miner")

BATCH_SIZE = 500


def batch_insert(table_name: str, records: List[dict]):
    """Helper to insert records into Supabase in chunks of BATCH_SIZE."""
    if not records:
        return

    db = get_service_client()
    total = len(records)

    for i in range(0, total, BATCH_SIZE):
        chunk = records[i : i + BATCH_SIZE]
        logger.debug("Inserting batch %d..%d into %s", i, i + len(chunk), table_name)
        db.table(table_name).insert(chunk).execute()


def mine_repository_task(repo_id: str, github_url: str, user_id: str, branch: Optional[str] = None):
    """Background task handler for repository mining."""
    logger.info("Starting background mining task for repo %s (url: %s)", repo_id, github_url)
    db = get_service_client()

    temp_dir = tempfile.mkdtemp(prefix="gitcompass_repo_")

    try:
        # Step 1: Update status -> cloning
        _, repo_name = parse_github_url(github_url)
        db.table("repositories").update(
            {
                "status": "cloning",
                "name": repo_name,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", repo_id).execute()

        # Step 2: Clone repository into temp dir
        clone_repository(github_url, temp_dir, branch)

        # Step 3: Update status -> mining
        db.table("repositories").update(
            {
                "status": "mining",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", repo_id).execute()

        # Step 4: Extract commits & diffs
        commits, file_diffs, total_commits, total_files = extract_git_history(
            temp_dir, repo_id, user_id
        )

        # Step 5: Batch insert data to Supabase
        logger.info("Writing %d commits to database...", len(commits))
        batch_insert("commits", commits)

        logger.info("Writing %d file diffs to database...", len(file_diffs))
        batch_insert("file_diffs", file_diffs)

        # Step 6: Mark repository as ready
        db.table("repositories").update(
            {
                "status": "ready",
                "total_commits": total_commits,
                "total_files": total_files,
                "error_message": None,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", repo_id).execute()

        logger.info("Finished background mining task for repo %s (ready)", repo_id)

    except Exception as exc:
        err_msg = str(exc)
        logger.error("Error during mining task for repo %s: %s\n%s", repo_id, err_msg, traceback.format_exc())

        try:
            db.table("repositories").update(
                {
                    "status": "error",
                    "error_message": err_msg[:500],  # Truncate if too long
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", repo_id).execute()
        except Exception as db_exc:
            logger.error("Failed to update error status for repo %s: %s", repo_id, db_exc)

    finally:
        # Step 7: Teardown temp directory
        safe_cleanup_dir(temp_dir)
