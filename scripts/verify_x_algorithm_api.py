import asyncio
import json
import os
from fastapi.testclient import TestClient
from supabase import create_client
from dotenv import load_dotenv

from app.main import app
from app.dependencies import get_current_user, get_db

load_dotenv()

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
db = create_client(supabase_url, supabase_key)

repo_name = "x-algorithm"
res = db.table("repositories").select("id").eq("name", repo_name).execute()
repo_id = res.data[0]["id"]

# Bypass auth for script
async def mock_get_current_user():
    return {"sub": "verify_script", "email": "verify@test.com", "role": "authenticated"}

# Use service role DB to bypass RLS for this script
async def mock_get_db():
    return db

app.dependency_overrides[get_current_user] = mock_get_current_user
app.dependency_overrides[get_db] = mock_get_db

client = TestClient(app)

print(f"Targeting repo: {repo_name} (ID: {repo_id})\n")

# 1. AI Summary
print("--- Requesting AI Summary ---")
res_summary = client.post(f"/api/ai/summary/{repo_id}", json={"force_refresh": True})
print(f"Status: {res_summary.status_code}")
summary_data = res_summary.json()
print("Structure:")
print(json.dumps(summary_data, indent=2)[:500] + "...\n")

# 2. Architecture Timeline
print("--- Requesting Architecture Timeline (Shifts) ---")
res_shifts = client.post(f"/api/ai/shifts/{repo_id}", json={"force_refresh": True})
print(f"Status: {res_shifts.status_code}")
shifts_data = res_shifts.json()
print("Structure:")
print(json.dumps(shifts_data, indent=2)[:500] + "...\n")

# 3. Development Story
print("--- Requesting Development Story ---")
res_story = client.post(f"/api/ai/story/{repo_id}", json={"force_refresh": True})
print(f"Status: {res_story.status_code}")
story_data = res_story.json()
print("Structure:")
print(json.dumps(story_data, indent=2)[:500] + "...\n")
