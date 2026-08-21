import os
import json
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
db = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_ROLE_KEY'])
res = db.table('ai_analysis_cache').select('analysis_type, content').execute()
for r in res.data:
    print(f"\n====== {r['analysis_type'].upper()} ======\n")
    print(json.dumps(r['content'], indent=2))
