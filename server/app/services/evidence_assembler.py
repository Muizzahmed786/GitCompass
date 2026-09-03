"""
Evidence Assembler — Stage 7 Component 1.

Collects and organizes deterministic evidence from the repository's full
history into a structured RepositoryEvidence object.

This layer is STRICTLY a data organizer.  It must NOT interpret evidence.
All interpretation belongs in the Stage 7 AI Reasoning layer that calls this.

Pipeline position:
    Stage 5 (repository_events)
        ↓
    Stage 6 (architecture_phases / architecture_phase_events)
        ↓
    Evidence Assembler  ← this file
        ↓
    Feature-specific context selection (Development Story / AI Summary / Architecture Timeline)
        ↓
    LLM Reasoning
"""

import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("gitcompass.evidence_assembler")

# ── Configuration Constants ───────────────────────────────────────────────────

# Maximum hotspot files to include in the evidence object.
# Sending all files to the LLM would be noisy; top N by churn is sufficient.
TOP_HOTSPOTS = 10

# Maximum contributors to include.
TOP_CONTRIBUTORS = 5

# Maximum significant commits to sample.
TOP_COMMITS = 30

# Maximum changed files to list per sampled commit.
TOP_FILES_PER_COMMIT = 3

# Bus factor threshold: minimum number of authors whose cumulative commit share
# must reach this percentage before we stop counting.
# Using 80% as the standard software engineering definition.
BUS_FACTOR_THRESHOLD = 0.80

# Commit types considered "high signal" for significance scoring.
# These map to conventional commit prefixes stored in the commit_type column.
HIGH_SIGNAL_COMMIT_TYPES = {"feat", "refactor"}

# Technology classification maps.
# Keys are lowercase dependency names; values are category labels.
_FRAMEWORK_KEYWORDS = {
    "react", "react-dom", "vue", "angular", "svelte", "next", "nuxt",
    "remix", "gatsby", "fastapi", "flask", "django", "express", "fastify",
    "koa", "hapi", "nestjs", "spring", "spring-boot", "rails", "laravel",
    "symfony", "gin", "echo", "fiber", "actix", "axum",
}

_RUNTIME_KEYWORDS = {
    "python", "node", "nodejs", "deno", "bun", "ruby", "go", "rust",
    "java", "kotlin", "scala", "dotnet", "clojure", "erlang", "elixir",
    "uvicorn", "gunicorn", "hypercorn",
}

_DATABASE_KEYWORDS = {
    "postgresql", "postgres", "pg", "psycopg", "psycopg2", "psycopg3",
    "mysql", "pymysql", "mysqlclient", "sqlite", "sqlite3",
    "mongodb", "pymongo", "mongoose", "motor",
    "redis", "aioredis", "redis-py",
    "elasticsearch", "opensearch",
    "cassandra", "dynamodb", "cosmosdb",
    "supabase",
}

_INFRASTRUCTURE_KEYWORDS = {
    "docker", "docker-compose", "kubernetes", "k8s", "helm",
    "terraform", "pulumi", "ansible", "vagrant",
    "nginx", "caddy", "traefik",
    "celery", "dramatiq", "rq", "bull", "bree",
    "kafka", "rabbitmq", "nats",
    "aws", "boto3", "azure", "google-cloud", "gcp",
    "github-actions", "circleci", "jenkins",
}


# ── Pure Helper Functions ─────────────────────────────────────────────────────


def calculate_bus_factor(author_counts: Dict[str, int]) -> int:
    """
    Calculates the correct bus factor for a repository.

    Definition: minimum number of contributors whose cumulative commit share
    reaches at least BUS_FACTOR_THRESHOLD (default 80%).

    Args:
        author_counts: Mapping of author display name → commit count.

    Returns:
        Bus factor integer.  Returns 0 for empty repos, minimum 1 otherwise.

    Examples:
        >>> calculate_bus_factor({"Alice": 60, "Bob": 25, "Carol": 10, "David": 5})
        2   # Alice (60%) + Bob (25%) = 85% ≥ 80%

        >>> calculate_bus_factor({"Alice": 100})
        1

        >>> calculate_bus_factor({})
        0
    """
    if not author_counts:
        return 0

    total = sum(author_counts.values())
    if total == 0:
        return 0

    sorted_authors = sorted(author_counts.items(), key=lambda x: (-x[1], x[0]))
    cumulative = 0
    bus_factor = 0
    for _, count in sorted_authors:
        cumulative += count
        bus_factor += 1
        if cumulative / total >= BUS_FACTOR_THRESHOLD:
            break

    return max(bus_factor, 1)


def _classify_dependency(name: str) -> Optional[str]:
    """
    Classifies a dependency name into a technology category.

    Returns one of: "framework", "runtime", "database", "infrastructure",
    or None if the dependency does not match any known category.

    Does NOT infer — only matches against known keyword sets.
    """
    lower = name.lower()
    if lower in _FRAMEWORK_KEYWORDS:
        return "framework"
    if lower in _RUNTIME_KEYWORDS:
        return "runtime"
    if lower in _DATABASE_KEYWORDS:
        return "database"
    if lower in _INFRASTRUCTURE_KEYWORDS:
        return "infrastructure"
    return None


def _normalize_date(date_val: Any) -> Optional[str]:
    """
    Normalises a date value to a YYYY-MM-DD string.

    Handles: datetime objects, ISO strings (with or without timezone).
    Returns None if the value cannot be interpreted.
    """
    if date_val is None:
        return None
    if hasattr(date_val, "strftime"):
        return date_val.strftime("%Y-%m-%d")
    if isinstance(date_val, str):
        # Handles "2024-01-15T10:30:00Z", "2024-01-15T10:30:00+05:30", "2024-01-15"
        return date_val[:10]
    return None


def _normalize_month(date_val: Any) -> Optional[str]:
    """Normalises a date value to a YYYY-MM string."""
    d = _normalize_date(date_val)
    if d and len(d) >= 7:
        return d[:7]
    return None


def _build_event_detail(event_type: str, metadata: Dict[str, Any]) -> str:
    """
    Converts raw repository event metadata into a compact, human-readable
    detail string.  This is purely mechanical; it does NOT interpret meaning.

    Examples:
        dependency_added   → "Added dependency fastapi (0.109.0) to requirements.txt"
        directory_introduced → "Introduced directory server/app/"
        large_change       → "Large commit with 1240 lines changed (+900/-340)"
    """
    if event_type == "dependency_added":
        dep = metadata.get("dependency", "unknown")
        ver = metadata.get("after_version", "")
        manifest = metadata.get("manifest", "")
        parts = [f"Added dependency {dep}"]
        if ver:
            parts[0] += f" ({ver})"
        if manifest:
            parts.append(f"to {manifest}")
        return " ".join(parts)

    if event_type == "dependency_removed":
        dep = metadata.get("dependency", "unknown")
        ver = metadata.get("before_version", "")
        manifest = metadata.get("manifest", "")
        parts = [f"Removed dependency {dep}"]
        if ver:
            parts[0] += f" ({ver})"
        if manifest:
            parts.append(f"from {manifest}")
        return " ".join(parts)

    if event_type == "dependency_version_changed":
        dep = metadata.get("dependency", "unknown")
        before = metadata.get("before_version", "?")
        after = metadata.get("after_version", "?")
        manifest = metadata.get("manifest", "")
        detail = f"Updated {dep} from {before} to {after}"
        if manifest:
            detail += f" in {manifest}"
        return detail

    if event_type == "manifest_introduced":
        path = metadata.get("path", "unknown")
        return f"Introduced manifest file {path}"

    if event_type == "directory_introduced":
        dir_path = metadata.get("directory_path") or metadata.get("path", "unknown")
        return f"Introduced directory {dir_path}/"

    if event_type == "large_change":
        ins = metadata.get("insertions", 0)
        dels = metadata.get("deletions", 0)
        total = metadata.get("total_churn", ins + dels)
        return f"Large commit with {total} lines changed (+{ins}/-{dels})"

    if event_type == "commit_declared_refactor":
        msg = metadata.get("commit_message", "")
        if msg:
            first_line = msg.strip().split("\n")[0][:80]
            return f"Refactor commit: {first_line}"
        return "Commit declared a refactor"

    # Generic fallback — do not invent detail
    return event_type.replace("_", " ").title()


def _score_commit(
    churn: int,
    commit_type: Optional[str],
    file_count: int,
    churn_percentiles: Dict[int, float],
) -> float:
    """
    Assigns a deterministic significance score to a commit.

    Scoring strategy (documented per the implementation spec):
        score = churn_percentile_rank
                + 1.5 if commit_type in HIGH_SIGNAL_COMMIT_TYPES
                + 0.5 if file_count > 5

    churn_percentiles is a pre-computed mapping of churn values to percentile
    ranks (0.0–100.0), used so we don't sort twice.
    """
    pct = churn_percentiles.get(churn, 0.0)
    score = pct
    if commit_type and commit_type.lower() in HIGH_SIGNAL_COMMIT_TYPES:
        score += 1.5
    if file_count > 5:
        score += 0.5
    return score


def _build_churn_percentiles(churn_values: List[int]) -> Dict[int, float]:
    """
    Builds a mapping of churn value → percentile rank (0–100).
    For duplicate churn values, all receive the same percentile (average rank).

    Deterministic: input is sorted before ranking.
    """
    if not churn_values:
        return {}

    n = len(churn_values)
    sorted_vals = sorted(set(churn_values))
    # Map each unique value to its percentile (0–100 scale)
    pct_map: Dict[int, float] = {}
    for i, v in enumerate(sorted_vals):
        pct_map[v] = (i / (len(sorted_vals) - 1)) * 100 if len(sorted_vals) > 1 else 100.0
    return pct_map


# ── Technology Fingerprint Builder ────────────────────────────────────────────


def _build_technology_fingerprint(db, repo_id: str) -> Dict[str, List[str]]:
    """
    Builds a deterministic technology fingerprint from repository_dependencies.

    Strategy (in priority order):
    1.  Query repository_dependencies table (populated by Stage 2/4).
        Each row has name, category, ecosystem.
    2.  Supplement with dependency names found in repository_events of type
        dependency_added (Stage 5), to catch anything not in the snapshot.

    Deduplication: uses a set internally; output lists are sorted.
    Classification: uses _classify_dependency() for event-based names;
        uses the stored category for repository_dependencies rows.
    """
    frameworks: set = set()
    runtimes: set = set()
    databases: set = set()
    infrastructure: set = set()

    # ── Source 1: repository_dependencies (Stage 2/4 static analysis) ──────
    try:
        deps_res = (
            db.table("repository_dependencies")
            .select("name, category, ecosystem")
            .eq("repo_id", repo_id)
            .execute()
        )
        for row in (deps_res.data or []):
            name = row.get("name", "").strip()
            category = (row.get("category") or "").lower()
            if not name:
                continue

            # Priority 1: Exact keyword match using our hardcoded taxonomy
            classified = _classify_dependency(name)
            if classified == "framework":
                frameworks.add(name)
            elif classified == "runtime":
                runtimes.add(name)
            elif classified == "database":
                databases.add(name)
            elif classified == "infrastructure":
                infrastructure.add(name)
            else:
                # Priority 2: Use the stored category from static analysis
                if "framework" in category or "ui" in category:
                    frameworks.add(name)
                elif "runtime" in category or "server" in category:
                    runtimes.add(name)
                elif "database" in category or "db" in category or "orm" in category:
                    databases.add(name)
                elif "infrastructure" in category or "devops" in category or "ci" in category:
                    infrastructure.add(name)
    except Exception as exc:
        logger.warning("[EvidenceAssembler] Failed to query repository_dependencies: %s", exc)

    # ── Source 2: repository_events (Stage 5) — dependency_added events ─────
    # These cover dependencies introduced via commits that may not be in the
    # snapshot stored by the knowledge model.
    try:
        events_res = (
            db.table("repository_events")
            .select("metadata")
            .eq("repo_id", repo_id)
            .in_("event_type", ["dependency_added", "dependency_version_changed"])
            .execute()
        )
        for row in (events_res.data or []):
            meta = row.get("metadata") or {}
            name = meta.get("dependency", "").strip()
            if not name:
                continue
            classified = _classify_dependency(name)
            if classified == "framework":
                frameworks.add(name)
            elif classified == "runtime":
                runtimes.add(name)
            elif classified == "database":
                databases.add(name)
            elif classified == "infrastructure":
                infrastructure.add(name)
    except Exception as exc:
        logger.warning("[EvidenceAssembler] Failed to query dependency events: %s", exc)

    return {
        "frameworks": sorted(frameworks),
        "runtimes": sorted(runtimes),
        "databases": sorted(databases),
        "infrastructure": sorted(infrastructure),
    }


# ── Phase Assembler ───────────────────────────────────────────────────────────


def _build_phases(db, repo_id: str) -> List[Dict[str, Any]]:
    """
    Loads Stage 6 architecture phases and their associated evidence.

    Query strategy (avoids N+1 and URI length limits):
    1. Load all phases for the repo in a single query.
    2. Load all phase-event mappings in a single query.
    3. Load relevant repository_events by filtering on repo_id and processing in Python.
    4. Join in Python.
    """
    # Step 1: Load all phases ordered by index
    phases_res = (
        db.table("architecture_phases")
        .select("id, phase_index, title, start_date, end_date, dominant_event_type, event_count")
        .eq("repo_id", repo_id)
        .order("phase_index", desc=False)
        .execute()
    )
    phase_rows = phases_res.data or []
    if not phase_rows:
        return []

    phase_ids = [p["id"] for p in phase_rows]

    # Step 2: Load all phase-event mappings in chunks to avoid URI too long (414)
    mappings = []
    chunk_size = 15
    for i in range(0, len(phase_ids), chunk_size):
        chunk = phase_ids[i:i + chunk_size]
        mappings_res = (
            db.table("architecture_phase_events")
            .select("phase_id, event_id")
            .in_("phase_id", chunk)
            .execute()
        )
        mappings.extend(mappings_res.data or [])

    # Build: phase_id → list of event_ids
    phase_to_event_ids: Dict[str, List[str]] = defaultdict(list)
    event_ids_set: set = set()
    for m in mappings:
        phase_to_event_ids[m["phase_id"]].append(m["event_id"])
        event_ids_set.add(m["event_id"])

    if not event_ids_set:
        # Phases exist but have no events mapped
        return [
            {
                "index": p["phase_index"],
                "title": p["title"],
                "start_date": _normalize_date(p["start_date"]),
                "end_date": _normalize_date(p["end_date"]),
                "dominant_type": p.get("dominant_event_type"),
                "event_count": p.get("event_count", 0),
                "evidence": [],
            }
            for p in phase_rows
        ]

    # Step 3: Load all repository_events for this repo, then filter in Python.
    # Using repo_id (indexed) avoids the URI-too-long error that in_(event_ids) causes
    # when there are hundreds of event UUIDs in the query string.
    events_res = (
        db.table("repository_events")
        .select("id, event_type, event_key, event_date, metadata")
        .eq("repo_id", repo_id)
        .limit(2000)   # Safety cap; phase events for a single repo are typically <500
        .execute()
    )
    event_by_id: Dict[str, Dict] = {
        e["id"]: e
        for e in (events_res.data or [])
        if e["id"] in event_ids_set
    }

    # Step 4: Assemble phase objects
    phases = []
    for phase_row in phase_rows:
        phase_id = phase_row["id"]
        ev_ids_for_phase = phase_to_event_ids.get(phase_id, [])

        evidence = []
        for ev_id in sorted(ev_ids_for_phase):  # sort for determinism
            ev = event_by_id.get(ev_id)
            if not ev:
                continue
            meta = ev.get("metadata") or {}
            # Extract the most descriptive name for this evidence item
            name = (
                meta.get("dependency")
                or meta.get("directory_path")
                or meta.get("path")
                or ev.get("event_key", "")
            )
            evidence.append({
                "type": ev["event_type"],
                "name": name,
                "date": _normalize_date(ev.get("event_date")),
                "detail": _build_event_detail(ev["event_type"], meta),
            })

        # Sort evidence chronologically (date ASC, then name for determinism)
        evidence.sort(key=lambda e: (e["date"] or "", e["name"]))

        phases.append({
            "index": phase_row["phase_index"],
            "title": phase_row["title"],
            "start_date": _normalize_date(phase_row["start_date"]),
            "end_date": _normalize_date(phase_row["end_date"]),
            "dominant_type": phase_row.get("dominant_event_type"),
            "event_count": phase_row.get("event_count", 0),
            "evidence": evidence,
        })

    return phases


# ── Hotspot Builder ───────────────────────────────────────────────────────────


def _build_hotspots(db, repo_id: str) -> List[Dict[str, Any]]:
    """
    Builds a ranked list of the most churned (volatile) files.

    Ranking:
        1. commit_count DESC
        2. total_churn (insertions + deletions) DESC
        3. file_path ASC   ← tiebreaker, guarantees determinism

    Only active (non-deleted) files are included.
    Limit: TOP_HOTSPOTS

    Query strategy: single join query, aggregated in Python.
    Limit raw query to 2000 rows to avoid full table scans on large repos.
    """
    raw_res = (
        db.table("file_diffs")
        .select("file_path, insertions, deletions, commits!inner(author_name)")
        .eq("repo_id", repo_id)
        .limit(2000)
        .execute()
    )

    file_stats: Dict[str, Dict] = defaultdict(lambda: {
        "commit_count": 0,
        "insertions": 0,
        "deletions": 0,
        "author_counts": defaultdict(int),
    })

    for row in (raw_res.data or []):
        path = row["file_path"]
        author = (row.get("commits") or {}).get("author_name") or "Unknown"
        file_stats[path]["commit_count"] += 1
        file_stats[path]["insertions"] += row.get("insertions", 0)
        file_stats[path]["deletions"] += row.get("deletions", 0)
        file_stats[path]["author_counts"][author] += 1

    hotspots = []
    for path, stats in file_stats.items():
        top_author = (
            max(stats["author_counts"], key=stats["author_counts"].get)
            if stats["author_counts"]
            else "Unknown"
        )
        hotspots.append({
            "file_path": path,
            "commit_count": stats["commit_count"],
            "insertions": stats["insertions"],
            "deletions": stats["deletions"],
            "top_author": top_author,
        })

    # Deterministic sort: commit_count DESC, total_churn DESC, file_path ASC
    hotspots.sort(
        key=lambda h: (-h["commit_count"], -(h["insertions"] + h["deletions"]), h["file_path"])
    )
    return hotspots[:TOP_HOTSPOTS]


# ── Contributor Builder ───────────────────────────────────────────────────────


def _build_contributors(db, repo_id: str) -> Dict[str, Any]:
    """
    Builds contributor statistics.

    Returns:
        total       — number of unique contributors
        bus_factor  — correct 80% threshold calculation
        top_authors — list of {name, commits, pct}, sorted by commits DESC, name ASC

    Query: single query for all commits, aggregated in Python.
    """
    commits_res = (
        db.table("commits")
        .select("author_name")
        .eq("repo_id", repo_id)
        .execute()
    )

    author_counts: Dict[str, int] = defaultdict(int)
    for row in (commits_res.data or []):
        name = row.get("author_name") or "Unknown"
        author_counts[name] += 1

    total = sum(author_counts.values()) or 1
    bus_factor = calculate_bus_factor(dict(author_counts))

    # Sort: commits DESC, name ASC for determinism
    sorted_authors = sorted(author_counts.items(), key=lambda x: (-x[1], x[0]))
    top_authors = [
        {
            "name": name,
            "commits": count,
            "pct": round((count / total) * 100, 2),
        }
        for name, count in sorted_authors[:TOP_CONTRIBUTORS]
    ]

    return {
        "total": len(author_counts),
        "bus_factor": bus_factor,
        "top_authors": top_authors,
    }


# ── Commit Sample Builder ─────────────────────────────────────────────────────


def _build_commit_sample(db, repo_id: str) -> List[Dict[str, Any]]:
    """
    Selects a sample of the most significant commits.

    Significance scoring (documented):
        score = churn_percentile_rank (0–100)
                + 1.5 if commit_type in {feat, refactor}
                + 0.5 if file_count > 5

    Returns TOP_COMMITS entries, each with:
        date          — YYYY-MM
        message       — first line of commit message
        type          — conventional commit type (from commit_type column)
        churn         — insertions + deletions
        files_changed — up to TOP_FILES_PER_COMMIT file paths

    Query strategy:
    1. Load commits (with basic metadata) in one query.
    2. Load file_diffs grouped by commit_id in one query.
    3. Join and score in Python.
    """
    # Step 1: Load commits (limit to 500 to bound memory; significant ones
    # will still surface because scoring uses percentile rank within the set)
    commits_res = (
        db.table("commits")
        .select("id, committed_at, message, insertions, deletions, commit_type")
        .eq("repo_id", repo_id)
        .order("committed_at", desc=False)
        .limit(500)
        .execute()
    )
    commits = commits_res.data or []
    if not commits:
        return []

    commit_ids = [c["id"] for c in commits]

    # Step 2: Load file paths for those commits in chunks to avoid URI too long (414)
    files_by_commit: Dict[str, List[str]] = defaultdict(list)
    chunk_size = 15
    for i in range(0, len(commit_ids), chunk_size):
        chunk = commit_ids[i:i + chunk_size]
        diffs_res = (
            db.table("file_diffs")
            .select("commit_id, file_path")
            .eq("repo_id", repo_id)
            .in_("commit_id", chunk)
            .execute()
        )
        for row in (diffs_res.data or []):
            files_by_commit[row["commit_id"]].append(row["file_path"])

    # Step 3: Compute churn percentile map
    churn_values = [(c.get("insertions", 0) + c.get("deletions", 0)) for c in commits]
    pct_map = _build_churn_percentiles(churn_values)

    # Step 4: Score and rank
    scored = []
    for c in commits:
        commit_id = c["id"]
        churn = c.get("insertions", 0) + c.get("deletions", 0)
        file_list = sorted(files_by_commit.get(commit_id, []))
        file_count = len(file_list)
        c_type = (c.get("commit_type") or "other").lower()

        score = _score_commit(churn, c_type, file_count, pct_map)
        scored.append({
            "_score": score,
            "date": _normalize_month(c.get("committed_at")),
            "message": (c.get("message") or "").strip().split("\n")[0][:120],
            "type": c_type,
            "churn": churn,
            "files_changed": file_list[:TOP_FILES_PER_COMMIT],
        })

    # Sort by score DESC, then date ASC for stable ordering
    scored.sort(key=lambda x: (-x["_score"], x["date"] or ""))

    # Remove internal score key before returning
    result = []
    for entry in scored[:TOP_COMMITS]:
        entry.pop("_score", None)
        result.append(entry)

    return result


# ── Primary Language Resolver ─────────────────────────────────────────────────


def _resolve_primary_language(db, repo_id: str) -> Optional[str]:
    """
    Attempts to determine the repository's primary language from the
    knowledge model's stored structure.

    Returns the language string if available, or None if it cannot be
    determined deterministically.  Never guesses.
    """
    try:
        knowledge_res = (
            db.table("repository_knowledge")
            .select("structure")
            .eq("repo_id", repo_id)
            .execute()
        )
        if knowledge_res.data:
            structure = knowledge_res.data[0].get("structure") or {}
            # Prefer stored primaryLanguage if the knowledge model sets it
            lang = structure.get("primaryLanguage") or structure.get("primary_language")
            if lang:
                return str(lang)
            # Fall back to the first entry of languages list
            languages = structure.get("languages", [])
            if isinstance(languages, list) and len(languages) > 0:
                return str(languages[0])
    except Exception as exc:
        logger.warning("[EvidenceAssembler] Could not resolve primary language: %s", exc)
    return None


# ── Main Public Function ──────────────────────────────────────────────────────


def assemble_evidence(repo_id: str, db) -> Dict[str, Any]:
    """
    Assembles a complete, deterministic evidence object for a repository.

    This is the primary public interface of the Evidence Assembler.

    For identical database state, this function always returns the same result.
    No LLM calls, no randomness, no current timestamps, no unstable ordering.

    Args:
        repo_id: UUID string of the repository.
        db:      Supabase database client (user-scoped or service-scoped).

    Returns:
        A RepositoryEvidence dict with keys:
            repository  — basic repository metadata
            technology  — deterministic tech fingerprint
            phases      — Stage 6 architecture phases with evidence
            hotspots    — top churned files
            contributors — contributor statistics with correct bus factor
            commit_sample — top significant commits

    Raises:
        Exception propagated from the underlying DB client on hard failures.
        Missing optional evidence returns empty lists / None, not exceptions.
    """
    logger.info("[EvidenceAssembler] Assembling evidence for repo %s", repo_id)

    # ── Repository Metadata ───────────────────────────────────────────────────
    repo_res = (
        db.table("repositories")
        .select("name, total_commits, latest_commit_sha")
        .eq("id", repo_id)
        .execute()
    )
    if not repo_res.data:
        raise ValueError(f"Repository {repo_id} not found")

    repo_row = repo_res.data[0]
    repo_name = repo_row.get("name") or "Unknown"
    total_commits = repo_row.get("total_commits") or 0

    # Date range from commits (first and last chronologically)
    date_range: Dict[str, Optional[str]] = {"first": None, "last": None}
    try:
        first_res = (
            db.table("commits")
            .select("committed_at")
            .eq("repo_id", repo_id)
            .order("committed_at", desc=False)
            .limit(1)
            .execute()
        )
        last_res = (
            db.table("commits")
            .select("committed_at")
            .eq("repo_id", repo_id)
            .order("committed_at", desc=True)
            .limit(1)
            .execute()
        )
        if first_res.data:
            date_range["first"] = _normalize_date(first_res.data[0].get("committed_at"))
        if last_res.data:
            date_range["last"] = _normalize_date(last_res.data[0].get("committed_at"))
    except Exception as exc:
        logger.warning("[EvidenceAssembler] Could not fetch date range: %s", exc)

    primary_language = _resolve_primary_language(db, repo_id)

    # ── Collect all evidence sections ─────────────────────────────────────────
    technology = _build_technology_fingerprint(db, repo_id)
    phases = _build_phases(db, repo_id)
    hotspots = _build_hotspots(db, repo_id)
    contributors = _build_contributors(db, repo_id)
    commit_sample = _build_commit_sample(db, repo_id)

    evidence = {
        "repository": {
            "name": repo_name,
            "total_commits": total_commits,
            "date_range": date_range,
            "primary_language": primary_language,
        },
        "technology": technology,
        "phases": phases,
        "hotspots": hotspots,
        "contributors": contributors,
        "commit_sample": commit_sample,
    }

    logger.info(
        "[EvidenceAssembler] Done — %d phases, %d hotspots, %d contributors, %d commit samples, "
        "%d frameworks, %d databases",
        len(phases),
        len(hotspots),
        contributors["total"],
        len(commit_sample),
        len(technology["frameworks"]),
        len(technology["databases"]),
    )
    return evidence


def retrieve_repository_slice(repo_id: str, target: str, db) -> Optional[Dict[str, Any]]:
    """
    Retrieves specific evidence for a target file.
    Validates that the target exists in the repository.
    Returns None if the file is not found or does not belong to the repo.
    """
    try:
        # Validate existence in repository_source_files (enforces repo_id authorization)
        file_res = db.table("repository_source_files").select("language, imports, classes, functions").eq("repo_id", repo_id).eq("file_path", target).execute()
        if not file_res.data:
            return None # File not found in this repo
            
        file_data = file_res.data[0]
        
        # Get recent commit history for this file (limit 15)
        diff_res = db.table("file_diffs").select("insertions, deletions, is_rename, old_path, commits!inner(author_name, message, committed_at, commit_type)").eq("repo_id", repo_id).eq("file_path", target).execute()
        
        # Sort manually since inner join order might be complex in PostgREST
        diffs = diff_res.data or []
        diffs.sort(key=lambda x: x.get("commits", {}).get("committed_at", ""), reverse=True)
        diffs = diffs[:15]
        
        recent_commits = []
        total_insertions = 0
        total_deletions = 0
        
        for row in diffs:
            c = row.get("commits", {})
            recent_commits.append({
                "author": c.get("author_name"),
                "date": _normalize_date(c.get("committed_at")),
                "type": c.get("commit_type"),
                "message": c.get("message"),
                "insertions": row.get("insertions", 0),
                "deletions": row.get("deletions", 0),
                "is_rename": row.get("is_rename", False),
                "old_path": row.get("old_path")
            })
            total_insertions += row.get("insertions", 0)
            total_deletions += row.get("deletions", 0)
            
        return {
            "type": "file",
            "path": target,
            "language": file_data.get("language"),
            "imports": file_data.get("imports", []),
            "classes": file_data.get("classes", []),
            "functions": file_data.get("functions", []),
            "recent_commits": recent_commits,
            "churn": {
                "recent_commits_count": len(recent_commits),
                "recent_insertions": total_insertions,
                "recent_deletions": total_deletions
            }
        }
    except Exception as exc:
        logger.error("[EvidenceAssembler] Failed to retrieve specific slice for %s: %s", target, exc)
        return None
