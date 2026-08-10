import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("Missing Supabase credentials")
    sys.exit(1)

# Unfortunately supabase-py doesn't have a direct raw SQL execution method.
# But wait, it doesn't matter, we can use psycopg2 since we don't have the DB string.
# Wait, Supabase provides REST API.
import requests

query = "ALTER TABLE public.repositories ADD COLUMN IF NOT EXISTS mining_progress INT DEFAULT 0;"

# We can't easily run arbitrary SQL through Supabase REST API without an RPC.
# Let's check if the project has a local supabase running.
