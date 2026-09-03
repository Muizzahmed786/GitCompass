import sys
import logging
from app.database import get_service_client

db = get_service_client()
repo = db.table('repositories').select('*').eq('name', 'x-algorithm').execute().data
if not repo:
    print('Repo not found.')
    sys.exit(0)

repo_id = repo[0]['id']
print(f'Repo ID: {repo_id}')

commits = db.table('commits').select('id, insertions, deletions').eq('repo_id', repo_id).execute().data
print(f'Commits: {len(commits)}')
for c in commits[:3]:
    print(c)

diffs = db.table('file_diffs').select('id, file_path').eq('repo_id', repo_id).execute().data
print(f'File diffs: {len(diffs)}')

events = db.table('repository_events').select('*').eq('repo_id', repo_id).execute().data
print(f'Events: {len(events)}')

if events:
    print(events[0])
