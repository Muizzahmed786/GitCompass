"""
Cloner service module.

Handles URL parsing, repo name extraction, and cloning repositories
into isolated temporary directories with strict cleanup guarantees.
"""

import logging
import os
import re
import shutil
import subprocess
import tempfile
from typing import Tuple, Optional

logger = logging.getLogger("gitcompass.cloner")


def parse_github_url(url: str) -> Tuple[str, str]:
    """Extract (owner, repo_name) from a GitHub URL."""
    cleaned = url.strip().rstrip("/")
    if cleaned.endswith(".git"):
        cleaned = cleaned[:-4]

    # Handle https://github.com/owner/repo or git@github.com:owner/repo
    match = re.search(r"github\.com[:/]([^/]+)/([^/]+)$", cleaned)
    if not match:
        raise ValueError(f"Could not parse GitHub owner and repository from URL: {url}")

    owner, repo_name = match.group(1), match.group(2)
    return owner, repo_name


def clone_repository(github_url: str, target_dir: str, branch: Optional[str] = None) -> str:
    """Clones a GitHub repository to target_dir.

    Uses `git clone --filter=blob:none` when possible to speed up download time
    while preserving full commit history and tree structures required for diff analysis.
    Falls back to a standard clone if blobless clone is unsupported or fails.
    """
    logger.info("Cloning repository %s -> %s", github_url, target_dir)

    # Standardize URL
    cleaned_url = github_url.strip()
    if not cleaned_url.endswith(".git") and not cleaned_url.startswith("git@"):
        cleaned_url = f"{cleaned_url}.git"

    # Command 1: Try blobless clone first (fastest for log extraction)
    cmd_blobless = [
        "git",
        "clone",
        "--filter=blob:none",
        "--no-checkout",
    ]
    if branch:
        cmd_blobless.extend(["--single-branch", "--branch", branch])
    cmd_blobless.extend([cleaned_url, target_dir])

    try:
        res = subprocess.run(
            cmd_blobless,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300,  # 5 min timeout for large repos
        )
        if res.returncode == 0:
            logger.info("Successfully cloned (blobless) %s", github_url)
            return target_dir
        else:
            logger.warning("Blobless clone failed (%s). Falling back to standard clone.", res.stderr.strip())
    except subprocess.TimeoutExpired:
        logger.warning("Blobless clone timed out. Trying standard clone.")
    except Exception as exc:
        logger.warning("Blobless clone exception: %s. Trying standard clone.", exc)

    # Command 2: Standard clone fallback (without checking out working tree files to save disk)
    cmd_standard = [
        "git",
        "clone",
        "--no-checkout",
    ]
    if branch:
        cmd_standard.extend(["--single-branch", "--branch", branch])
    cmd_standard.extend([cleaned_url, target_dir])

    res = subprocess.run(
        cmd_standard,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=600,  # 10 min timeout
    )
    if res.returncode != 0:
        raise RuntimeError(f"Git clone failed: {res.stderr.strip()}")

    logger.info("Successfully cloned (standard) %s", github_url)
    return target_dir


def safe_cleanup_dir(dir_path: str):
    """Safely removes directory tree if it exists."""
    if dir_path and os.path.exists(dir_path):
        try:
            shutil.rmtree(dir_path, ignore_errors=True)
            logger.info("Cleaned up temp directory: %s", dir_path)
        except Exception as exc:
            logger.error("Failed to clean up temp directory %s: %s", dir_path, exc)
