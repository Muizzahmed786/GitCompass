import asyncio
import json
import os
from supabase import create_client
from dotenv import load_dotenv

from app.services.evidence_assembler import assemble_evidence
from app.services.ai_service import REPOSITORY_INTELLIGENCE_PROMPT

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
db = create_client(supabase_url, supabase_key)

repo_name = "x-algorithm"

# Get repo id
res = db.table("repositories").select("id").eq("name", repo_name).execute()
repo_id = res.data[0]["id"]

# Get evidence
evidence = assemble_evidence(repo_id, db)

compact_summary_evidence = json.dumps({
    "repository": evidence.get("repository"),
    "technology": evidence.get("technology"),
    "phases": evidence.get("phases"),
    "hotspots": evidence.get("hotspots"),
    "contributors": evidence.get("contributors"),
    "commit_sample": evidence.get("commit_sample")
}, separators=(',', ':'))

compact_shifts_evidence = json.dumps({
    "repository": evidence.get("repository"),
    "technology": evidence.get("technology"),
    "phases": evidence.get("phases")
}, separators=(',', ':'))

print("================ DEVELOPMENT STORY / SUMMARY EVIDENCE ================\n")
print(compact_summary_evidence[:1000] + "\n... [TRUNCATED] ...\n")
print("================ ARCHITECTURE TIMELINE EVIDENCE ================\n")
print(compact_shifts_evidence[:1000] + "\n... [TRUNCATED] ...\n")
