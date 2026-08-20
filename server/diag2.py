import sys
import logging
import tempfile
import shutil
import traceback
from app.services.cloner import clone_repository
from app.services.extractor import extract_git_history
from app.services.evolution_analyzer import analyze_evolution
from app.database import get_service_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diag")

db = get_service_client()
repo = db.table('repositories').select('*').eq('name', 'x-algorithm').execute().data
if not repo:
    print('Repo not found.')
    sys.exit(0)

repo_id = repo[0]['id']
github_url = repo[0]['github_url']

temp_dir = tempfile.mkdtemp(prefix="gitcompass_diag_")
try:
    logger.info(f"Cloning {github_url} to {temp_dir}")
    clone_repository(github_url, temp_dir)
    
    logger.info("Extracting history...")
    commits, file_diffs, *_ = extract_git_history(temp_dir, repo_id, 'dummy_user')
    
    logger.info(f"Extracted {len(commits)} commits, {len(file_diffs)} diffs")
    
    logger.info("Running analyze_evolution...")
    analyze_evolution(repo_id, temp_dir, commits, file_diffs)
    logger.info("Done analyze_evolution without unhandled exceptions.")
except Exception as e:
    logger.error("Exception occurred:", exc_info=True)
finally:
    shutil.rmtree(temp_dir, ignore_errors=True)
