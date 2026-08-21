"""
Stage 7 Evidence Assembler — Live Verification Script.

Usage (from server/):
    .venv/Scripts/python.exe verify_evidence.py <repo_id>

If no repo_id is provided, it queries the first ready repository.
"""
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import get_service_client
from app.services.evidence_assembler import assemble_evidence


def find_repo_id(db, name_hint: str = None) -> str:
    """Find a repository by partial name or return the first ready one."""
    if name_hint:
        res = (
            db.table("repositories")
            .select("id, name, status, total_commits")
            .ilike("name", f"%{name_hint}%")
            .eq("status", "ready")
            .limit(1)
            .execute()
        )
    else:
        res = (
            db.table("repositories")
            .select("id, name, status, total_commits")
            .eq("status", "ready")
            .limit(1)
            .execute()
        )
    if not res.data:
        raise RuntimeError("No ready repositories found.")
    row = res.data[0]
    print(f"[Verifier] Using repository: {row['name']} (id: {row['id']}, commits: {row['total_commits']})")
    return row["id"]


def print_evidence_summary(evidence: dict):
    repo = evidence["repository"]
    tech = evidence["technology"]
    phases = evidence["phases"]
    hotspots = evidence["hotspots"]
    contributors = evidence["contributors"]
    commit_sample = evidence["commit_sample"]

    print()
    print("=" * 70)
    print("REPOSITORY EVIDENCE SUMMARY")
    print("=" * 70)

    print(f"\nRepository:      {repo['name']}")
    print(f"Total commits:   {repo['total_commits']}")
    dr = repo["date_range"]
    print(f"Date range:      {dr.get('first')} -> {dr.get('last')}")
    print(f"Primary lang:    {repo.get('primary_language') or '(not detected)'}")

    print("\n── Technology ─────────────────────────────────────────────────")
    print(f"Frameworks:      {', '.join(tech['frameworks']) or '(none detected)'}")
    print(f"Runtimes:        {', '.join(tech['runtimes']) or '(none detected)'}")
    print(f"Databases:       {', '.join(tech['databases']) or '(none detected)'}")
    print(f"Infrastructure:  {', '.join(tech['infrastructure']) or '(none detected)'}")

    print("\n── Architecture Phases ────────────────────────────────────────")
    print(f"Phase count:     {len(phases)}")
    for p in phases:
        print(f"  [{p['index']}] {p['start_date']} → {p['end_date']}  |  {p['title']}")
        print(f"       Events: {p['event_count']}  |  Dominant: {p.get('dominant_type')}")
        for ev in p["evidence"][:3]:
            print(f"       • {ev['type']}: {ev['detail']}")
        if len(p["evidence"]) > 3:
            print(f"       … and {len(p['evidence']) - 3} more evidence items")

    print("\n── Hotspots ───────────────────────────────────────────────────")
    print(f"Top {len(hotspots)} files:")
    for h in hotspots:
        print(f"  {h['commit_count']:>4} commits  +{h['insertions']}/-{h['deletions']}  "
              f"{h['file_path']}  (top: {h['top_author']})")

    print("\n── Contributors ───────────────────────────────────────────────")
    print(f"Total:           {contributors['total']}")
    print(f"Bus factor:      {contributors['bus_factor']}  (80% threshold)")
    for a in contributors["top_authors"]:
        bar = "█" * max(1, int(a["pct"] / 5))
        print(f"  {a['name']:<25} {a['commits']:>5} commits  ({a['pct']:.1f}%)  {bar}")

    print("\n── Significant Commit Sample ──────────────────────────────────")
    print(f"Sampled commits: {len(commit_sample)}")
    for i, c in enumerate(commit_sample[:10]):
        files_str = ", ".join(c["files_changed"]) or "(none)"
        print(f"  [{i+1:>2}] {c['date']}  [{c['type']:<10}]  churn={c['churn']:<6}  "
              f"{c['message'][:60]}")
        print(f"         Files: {files_str}")
    if len(commit_sample) > 10:
        print(f"  … and {len(commit_sample) - 10} more sampled commits")

    print("\n" + "=" * 70)
    print("Evidence assembly: OK")
    print("=" * 70)


if __name__ == "__main__":
    db = get_service_client()

    name_hint = sys.argv[1] if len(sys.argv) > 1 else "x-algorithm"
    repo_id = find_repo_id(db, name_hint)

    evidence = assemble_evidence(repo_id, db)
    print_evidence_summary(evidence)
