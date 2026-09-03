import os
import sys
import asyncio

sys.path.append(os.path.join(os.path.dirname(__file__), "server"))
from app.services.miner import mine_repository_task
from app.database import get_service_client

def run_mine():
    db = get_service_client()
    res = db.table("repositories").select("id, name, github_url, user_id").eq("name", "x-algorithm").execute()
    
    if not res.data:
        print("x-algorithm not found in database.")
        return
        
    repo = res.data[0]
    print(f"Clearing old data for {repo['name']} (ID: {repo['id']})")
    db.table("commits").delete().eq("repo_id", repo["id"]).execute()
    db.table("repository_events").delete().eq("repo_id", repo["id"]).execute()
    
    print(f"Re-mining {repo['name']} (ID: {repo['id']})")
    mine_repository_task(repo["id"], repo["github_url"], repo["user_id"])
    print("Done")

if __name__ == "__main__":
    run_mine()
