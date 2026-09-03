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
import traceback
from typing import List, Any, Optional

from app.database import get_service_client
from app.services.cloner import clone_repository, parse_github_url, safe_cleanup_dir
from app.services.extractor import extract_git_history
from app.services.structure_analyzer import analyze_repository_structure
from app.services.dependency_analyzer import analyze_dependencies
from app.services.source_analyzer import analyze_source_code
from app.services.knowledge_model import replace_knowledge_model
from app.services.evolution_analyzer import analyze_evolution
from app.services.phase_analyzer import analyze_phases

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

        # Step 3: Update status -> mining and progress -> 0
        db.table("repositories").update(
            {
                "status": "mining",
                "mining_progress": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", repo_id).execute()

        # Define progress callback
        def handle_progress(pct: int):
            try:
                db.table("repositories").update({"mining_progress": pct}).eq("id", repo_id).execute()
            except Exception as p_exc:
                logger.warning("Failed to update progress for repo %s: %s", repo_id, p_exc)

        # Step 4: Extract commits & diffs
        commits, file_diffs, total_commits, total_files, latest_commit_sha = extract_git_history(
            temp_dir, repo_id, user_id, progress_callback=handle_progress
        )

        # Step 5: Batch insert data to Supabase
        logger.info("Writing %d commits to database...", len(commits))
        batch_insert("commits", commits)

        logger.info("Writing %d file diffs to database...", len(file_diffs))
        batch_insert("file_diffs", file_diffs)
        
        if latest_commit_sha:
            logger.info("Running deterministic analyzers for Knowledge Model...")
            structure = analyze_repository_structure(temp_dir)
            dependencies = analyze_dependencies(temp_dir, structure.manifestFiles)
            source_code = analyze_source_code(temp_dir, structure.sourceFiles)
            replace_knowledge_model(repo_id, latest_commit_sha, structure, dependencies, source_code)

            try:
                logger.info("Running deterministic evolution analysis (Stage 5)...")
                analyze_evolution(repo_id, temp_dir, commits, file_diffs)
            except Exception as e:
                logger.error("Stage 5 evolution analysis failed for repo %s: %s", repo_id, e, exc_info=True)

            try:
                logger.info("Running architecture phase analysis (Stage 6)...")
                analyze_phases(repo_id)
            except Exception as e:
                logger.error("Stage 6 phase analysis failed for repo %s: %s", repo_id, e, exc_info=True)

        # Step 6: Mark repository as ready
        # Explicit completion ordering: mining_progress = 100 first, then status = "ready"
        db.table("repositories").update({"mining_progress": 100}).eq("id", repo_id).execute()

        update_payload = {
            "status": "ready",
            "total_commits": total_commits,
            "total_files": total_files,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if latest_commit_sha:
            update_payload["latest_commit_sha"] = latest_commit_sha

        db.table("repositories").update(update_payload).eq("id", repo_id).execute()

        logger.info("Finished background mining task for repo %s (ready)", repo_id)

    except Exception as exc:
        err_msg = str(exc)
        logger.error("Error during mining task for repo %s: %s\n%s", repo_id, err_msg, traceback.format_exc())

        try:
            db.table("repositories").update(
                {
                    "status": "error",
                    "error_message": err_msg[:500],  # Truncate if too long
                    "mining_progress": 0,            # Clear progress on error
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", repo_id).execute()
        except Exception as db_exc:
            logger.error("Failed to update error status for repo %s: %s", repo_id, db_exc)

    finally:
        # Step 7: Teardown temp directory
        safe_cleanup_dir(temp_dir)


def delete_repo_background(repo_id: str, db: Any):
    """Background task to delete repository tables step-by-step and report progress."""
    try:
        large_tables = [
            "file_diffs",
            "commits",
            "repository_events",
            "repository_source_files",
            "repository_dependencies"
        ]
        total_steps = len(large_tables) + 1
        
        for i, table_name in enumerate(large_tables):
            try:
                db.table(table_name).delete().eq("repo_id", repo_id).execute()
            except Exception as e:
                logger.warning("Failed to manually cascade delete %s for %s: %s", table_name, repo_id, e)
                
            progress = int(((i + 1) / total_steps) * 100)
            try:
                db.table("repositories").update({"mining_progress": progress}).eq("id", repo_id).execute()
            except Exception:
                pass

        db.table("repositories").delete().eq("id", repo_id).execute()
    except Exception as exc:
        logger.error("Background delete failed for repository %s: %s", repo_id, exc)
        try:
            db.table("repositories").update({"status": "failed", "mining_progress": 0}).eq("id", repo_id).execute()
        except Exception:
            pass

def sync_repository_task(repo_id: str, github_url: str, user_id: str, branch: Optional[str] = None):
    """Background task handler for incremental delta repository sync."""
    logger.info("Starting background incremental sync task for repo %s (url: %s)", repo_id, github_url)
    db = get_service_client()

    repo_res = db.table("repositories").select("latest_commit_sha, total_commits, total_files").eq("id", repo_id).execute()
    existing_repo = repo_res.data[0] if repo_res.data else {}
    since_sha = existing_repo.get("latest_commit_sha")

    temp_dir = tempfile.mkdtemp(prefix="gitcompass_sync_")

    try:
        # Step 1: Update status -> mining and progress -> 0
        db.table("repositories").update(
            {
                "status": "mining",
                "mining_progress": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", repo_id).execute()

        # Define progress callback
        def handle_sync_progress(pct: int):
            try:
                db.table("repositories").update({"mining_progress": pct}).eq("id", repo_id).execute()
            except Exception as p_exc:
                logger.warning("Failed to update sync progress for repo %s: %s", repo_id, p_exc)

        # Step 2: Clone repository into temp dir
        clone_repository(github_url, temp_dir, branch)

        # Step 3: Incremental extract commits & diffs
        commits, file_diffs, new_commits_cnt, new_files_cnt, latest_commit_sha = extract_git_history(
            temp_dir, repo_id, user_id, since_sha=since_sha, progress_callback=handle_sync_progress
        )

        if commits:
            logger.info("Writing %d new delta commits to database for repo %s...", len(commits), repo_id)
            batch_insert("commits", commits)
            batch_insert("file_diffs", file_diffs)
            
        if latest_commit_sha and latest_commit_sha != since_sha:
            logger.info("Running deterministic analyzers for Knowledge Model on sync...")
            structure = analyze_repository_structure(temp_dir)
            dependencies = analyze_dependencies(temp_dir, structure.manifestFiles)
            source_code = analyze_source_code(temp_dir, structure.sourceFiles)
            replace_knowledge_model(repo_id, latest_commit_sha, structure, dependencies, source_code)

            try:
                logger.info("Running deterministic evolution analysis on sync...")
                analyze_evolution(repo_id, temp_dir, commits, file_diffs)
            except Exception as e:
                logger.error("Stage 5 evolution analysis failed during sync for repo %s: %s", repo_id, e, exc_info=True)

        # Step 4: Re-calculate totals and mark ready
        db.table("repositories").update({"mining_progress": 100}).eq("id", repo_id).execute()

        total_commits = (existing_repo.get("total_commits") or 0) + len(commits)
        update_payload = {
            "status": "ready",
            "total_commits": total_commits,
            "error_message": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if latest_commit_sha:
            update_payload["latest_commit_sha"] = latest_commit_sha

        db.table("repositories").update(update_payload).eq("id", repo_id).execute()
        logger.info("Finished incremental sync task for repo %s (added %d new commits)", repo_id, len(commits))

    except Exception as exc:
        err_msg = str(exc)
        logger.error("Error during sync task for repo %s: %s\n%s", repo_id, err_msg, traceback.format_exc())

        try:
            db.table("repositories").update(
                {
                    "status": "ready",  # Revert back to ready status on sync error
                    "error_message": f"Sync failed: {err_msg[:300]}",
                    "mining_progress": 0,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", repo_id).execute()
        except Exception as db_exc:
            logger.error("Failed to update status for repo %s: %s", repo_id, db_exc)

    finally:
        safe_cleanup_dir(temp_dir)

