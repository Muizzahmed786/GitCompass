# File Input / Output Specification Map (`FILE_CONTRACTS.md`)

> **Location:** `docs/FILE_CONTRACTS.md`  
> **Purpose:** Comprehensive directory of input parameters, expected outputs, return types, and side effects for **every single file** in the GitCompass codebase.

---

## 📌 Standard Requirement for Future Development

Whenever a file is added, modified, or refactored:
1. **Document Inputs & Outputs:** You MUST add or update its contract in this file.
2. **Specify Input Contracts:** Include environment variables, HTTP headers/payloads, function arguments, props, or database state required.
3. **Specify Output Contracts:** Include return values, HTTP response schemas, rendered UI components, or database mutations.

---

## ⚙️ Backend — Core & System Entry Points

### [server/app/main.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/main.py)
- **Role:** FastAPI application initialization, lifespan lifecycle, and router mounting.
- **Inputs:**
  - `app.config.settings` (`APP_NAME`, `DEBUG`, `SUPABASE_URL`)
- **Outputs / Returns:**
  - FastAPI instance (`app`) with mounted routers (`/api/health`, `/api/repositories`, `/api/analytics`).
  - `/` route returns `{"message": "Welcome to GitCompass", "docs": "/docs"}`.
  - Console startup & shutdown logs.

---

### [server/app/config.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/config.py)
- **Role:** Application configuration loader backed by `pydantic-settings`.
- **Inputs:**
  - Environment variables from `server/.env` (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET`, `APP_NAME`, `DEBUG`).
- **Outputs / Returns:**
  - `settings`: Immutable `Settings` singleton instance containing validated system config attributes.

---

### [server/app/database.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/database.py)
- **Role:** Supabase database client factories.
- **Inputs:**
  - `get_user_client(jwt: str)`: Requires a raw Supabase Bearer JWT string.
  - `get_service_client()`: Reads `SUPABASE_SERVICE_ROLE_KEY` from `settings`.
- **Outputs / Returns:**
  - `get_user_client`: Returns Supabase `Client` configured with user authorization headers (enforces PostgreSQL Row-Level Security).
  - `get_service_client`: Returns Supabase `Client` with service-role privileges (bypasses RLS for background workers).

---

### [server/app/dependencies.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/dependencies.py)
- **Role:** FastAPI dependency injection handlers for JWT authentication and database access.
- **Inputs:**
  - `request: Request` containing `Authorization: Bearer <jwt>` HTTP header.
- **Outputs / Returns:**
  - `get_current_user`: Returns validated user dict `{"sub": user_id, "email": email, "role": role}` or raises `HTTPException(401)`.
  - `get_db`: Returns JWT-scoped user Supabase `Client` or raises `HTTPException(401)`.

---

### [server/app/core/redis.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/core/redis.py)
- **Role:** Centralized Redis client instance provider.
- **Inputs:**
  - Docker DNS network target host: `"redis"`
  - TCP Port: `6379`
  - Client parameter: `decode_responses=True`
- **Outputs / Returns:**
  - `redis_client`: Initialized `redis.Redis` client instance for executing key-value, caching, and ping commands (`redis_client.ping()`).

---

### [docker-compose.yml](file:///c:/Users/mulla/Desktop/Projects/GitCompass/docker-compose.yml)
- **Role:** Multi-container Docker orchestration for GitCompass.
- **Inputs:**
  - Service `server`: Docker context `./server`, environment file `./server/.env`, port forwarding `8000:8000`, dependency `redis`.
  - Service `redis`: Image `redis:7-alpine`, container `gitcompass-redis`, port forwarding `6379:6379`.
- **Outputs / Returns:**
  - Running container stack with networked FastAPI backend (`gitcompass-server`) and Redis server (`gitcompass-redis`).

---

### [server/Dockerfile](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/Dockerfile)
- **Role:** Docker image build manifest for FastAPI application.
- **Inputs:**
  - Base image: `python:3.13-slim`
  - Dependencies: `requirements.txt`
  - Source context: `server/` (filtered by `.dockerignore`)
- **Outputs / Returns:**
  - Built image `gitcompass-server:latest` exposing port 8000 with entrypoint `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

---

## 🌐 Backend — API Routers

### [server/app/routers/health.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/health.py)
- **Role:** API status and system diagnostics endpoints.
- **Inputs:**
  - `GET /api/health`
  - `GET /api/health/db` (Requires `db: UserDB`)
- **Outputs / Returns:**
  - `GET /api/health` -> `{"status": "ok", "app": "GitCompass", "version": "0.1.0"}`
  - `GET /api/health/db` -> `{"status": "ok", "database": "connected", "latency_ms": float}` or `HTTPException(503)`

---

### [server/app/routers/repositories.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/repositories.py)
- **Role:** REST CRUD operations and mining background task triggers for user repositories.
- **Inputs:**
  - `POST /api/repositories`: Body `RepositoryCreate` (`github_url: str`, `branch: Optional[str]`), Headers `Authorization`.
  - `GET /api/repositories`: Headers `Authorization`.
  - `GET /api/repositories/{repo_id}`: Path `repo_id: str`, Headers `Authorization`.
  - `DELETE /api/repositories/{repo_id}`: Path `repo_id: str`, Headers `Authorization`.
  - `POST /api/repositories/{repo_id}/sync`: Path `repo_id: str`, Headers `Authorization`.
- **Outputs / Returns:**
  - `POST /api/repositories`: Returns `RepositoryResponse` JSON (HTTP 202 Accepted); triggers background task `mine_repository_task`.
  - `GET /api/repositories`: Returns `RepositoryListResponse` `{"repositories": [...], "count": int}`.
  - `GET /api/repositories/{repo_id}`: Returns `RepositoryResponse` object or HTTP 404.
  - `DELETE /api/repositories/{repo_id}`: Returns `{"status": "deleted", "id": repo_id}` (cascades commit & diff records).
  - `POST /api/repositories/{repo_id}/sync`: Returns `RepositoryResponse` (HTTP 202 Accepted); triggers background task `sync_repository_task`.

---

### [server/app/routers/analytics.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/analytics.py)
- **Role:** Endpoints for code hotspots, temporal coupling, bus factor, and summary statistics.
- **Inputs:**
  - `GET /api/analytics/{repo_id}/hotspots`: `start_date`, `end_date`, `commit_type`.
  - `GET /api/analytics/{repo_id}/temporal-coupling`: `threshold` (float), `max_commit_files` (int).
  - `GET /api/analytics/{repo_id}/bus-factor`
  - `GET /api/analytics/{repo_id}/summary`
- **Outputs / Returns:**
  - `hotspots`: Returns `List[HotspotResponse]` (file path, insertion/deletion totals, author counts, orphan risk flags).
  - `temporal-coupling`: Returns `List[TemporalCouplingItem]` (`file_a`, `file_b`, `co_changes`, `degree`).
  - `bus-factor`: Returns `BusFactorResponse` (`repo_bus_factor`, `top_contributors`, `orphan_risk_files`).
  - `summary`: Returns `SummaryAnalyticsResponse` overview dict.

---

## 🛠 Backend — Services & Mining Engine

### [server/app/services/cloner.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/cloner.py)
- **Role:** GitHub URL parsing, blobless/standard git cloning, and filesystem cleanup.
- **Inputs:**
  - `parse_github_url(url: str)`: GitHub repository URL.
  - `clone_repository(github_url: str, target_dir: str, branch: Optional[str])`: Target destination folder.
  - `safe_cleanup_dir(dir_path: str)`: Local directory path to delete.
- **Outputs / Returns:**
  - `parse_github_url`: Returns tuple `(owner: str, repo_name: str)`.
  - `clone_repository`: Clones repository onto disk; returns `target_dir` string or raises `RuntimeError`.
  - `safe_cleanup_dir`: Removes folder tree safely; returns `None`.

---

### [server/app/services/extractor.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/extractor.py)
- **Role:** Git log streaming, numstat parsing, conventional commit classification, and gitignore filtering.
- **Inputs:**
  - `classify_commit_type(message: str)`: Raw commit message string.
  - `parse_git_path(path_str: str)`: Git numstat raw path.
  - `extract_git_history(repo_dir: str, repo_id: str, user_id: str, since_sha: Optional[str])`: Local repository directory path & metadata IDs.
- **Outputs / Returns:**
  - `classify_commit_type`: Returns classified type string (`feat`, `fix`, `refactor`, `docs`, etc.).
  - `parse_git_path`: Returns tuple `(current_path, old_path, is_rename)`.
  - `extract_git_history`: Returns tuple `(commits_list, file_diffs_list, total_commits, total_files, latest_commit_sha)`.

---

### [server/app/services/miner.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/miner.py)
- **Role:** Async background task orchestrator for repository mining and incremental synchronization.
- **Inputs:**
  - `batch_insert(table_name: str, records: List[dict])`: Record chunks.
  - `mine_repository_task(repo_id: str, github_url: str, user_id: str, branch: Optional[str])`: Background task params.
  - `sync_repository_task(repo_id: str, github_url: str, user_id: str, branch: Optional[str])`: Background sync params.
- **Outputs / Returns:**
  - `batch_insert`: Writes record batches to Supabase via service client.
  - `mine_repository_task` / `sync_repository_task`: Updates repository DB status (`pending` -> `cloning` -> `mining` -> `ready` / `error`), writes commits and diffs, cleans up temp directories.

---

## 📋 Backend — Data Schemas

### [server/app/schemas/repository.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/schemas/repository.py)
- **Role:** Pydantic validation models for repository requests and API responses.
- **Inputs:**
  - Raw JSON request payloads for repository creation and retrieval.
- **Outputs / Returns:**
  - `RepositoryCreate`: Validated Pydantic model (`github_url`, `branch`).
  - `RepositoryResponse`: Validated model matching database table schema.
  - `RepositoryListResponse`: Validated model list (`repositories`, `count`).

---

## 🗄 Supabase Database Migrations

### [server/supabase/migrations/001_initial_schema.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/001_initial_schema.sql)
- **Role:** Core database table definitions (`profiles`, `repositories`, `commits`, `file_diffs`), trigger functions, and initial Row-Level Security (RLS) policies.
- **Inputs:** PostgreSQL migration execution.
- **Outputs:** Database schema tables with primary keys, foreign keys (`ON DELETE CASCADE`), indexes, and user-isolation policies.

---

### [server/supabase/migrations/002_analytics_rpc.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/002_analytics_rpc.sql)
- **Role:** Custom PostgreSQL RPC function definitions for analytics queries.
- **Inputs:** Parameters `p_repo_id`, `p_limit`.
- **Outputs:** Stored procedures returning aggregated commit & hotspot table records.

---

### [server/supabase/migrations/003_add_is_deleted.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/003_add_is_deleted.sql)
- **Role:** Alters `file_diffs` table to add `is_deleted` boolean flag.
- **Inputs:** Migration run.
- **Outputs:** `file_diffs.is_deleted` column added with default `FALSE`.

---

### [server/supabase/migrations/004_phase_4_5_schema.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/004_phase_4_5_schema.sql)
- **Role:** Adds `commit_type` column to `commits` table and indexing for conventional commit analytics.
- **Inputs:** Migration run.
- **Outputs:** `commits.commit_type` column added with composite index on `(repo_id, commit_type)`.

---

### [server/supabase/migrations/007_api_role_grants.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/007_api_role_grants.sql)
- **Role:** Explicitly grants `SELECT, INSERT, UPDATE, DELETE` privileges to the `authenticated` and `service_role` roles for all tables in the `public` schema.
- **Inputs:** Migration run.
- **Outputs:** Modifies Postgres ACLs and `pg_default_acl` to ensure the local Supabase API can perform DML operations.

---

## 💻 Frontend — Application & Routing

### [client/src/main.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/main.jsx)
- **Role:** React DOM application root entry point.
- **Inputs:** DOM element `#root`.
- **Outputs:** Renders `<App />` component inside React `StrictMode`.

---

### [client/src/App.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/App.jsx)
- **Role:** Auth-gated router & Supabase session lifecycle manager.
- **Inputs:**
  - Supabase Auth state (`supabase.auth.getSession()`, `onAuthStateChange`).
- **Outputs:**
  - Unauthenticated: Renders `<Login />`.
  - Authenticated: Renders `<BrowserRouter><Layout><Routes... /></Layout></BrowserRouter>`.

---

### [client/src/index.css](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/index.css)
- **Role:** Global design tokens, Tailwind CSS directives, typography imports, and custom animations.
- **Inputs:** CSS variables and custom utility rules.
- **Outputs:** Global stylesheet applied across entire React application.

---

## 🔌 Frontend — Client Libraries

### [client/src/lib/api.js](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/lib/api.js)
- **Role:** HTTP REST client wrapper for communicating with FastAPI backend via Vite proxy.
- **Inputs:**
  - `path`: Relative path string (e.g. `/api/repositories`).
  - `options`: Fetch configuration (method, body, headers).
  - Current Supabase access token from session.
- **Outputs:**
  - Attaches `Authorization: Bearer <token>` header.
  - Returns parsed JSON response promise or throws HTTP error.

---

### [client/src/lib/supabase.js](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/lib/supabase.js)
- **Role:** Browser Supabase JS client singleton instance.
- **Inputs:**
  - `import.meta.env.VITE_SUPABASE_URL`
  - `import.meta.env.VITE_SUPABASE_ANON_KEY`
- **Outputs:**
  - Exported `supabase` client instance for OAuth authentication and client queries.

---

## 📄 Frontend — Pages & Views

### [client/src/pages/Login.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/pages/Login.jsx)
- **Role:** Login view providing GitHub OAuth authentication trigger.
- **Inputs:** User click interaction on "Continue with GitHub" button.
- **Outputs:** Invokes `supabase.auth.signInWithOAuth({ provider: 'github' })`.

---

### [client/src/pages/Dashboard.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/pages/Dashboard.jsx)
- **Role:** User dashboard listing tracked repositories, status polling, and repository addition modal.
- **Inputs:** User props (`user`), API response data from `/api/repositories`, GitHub API public branches.
- **Outputs:**
  - Renders repository grid, mining status badges, commit counts, retry controls, and add/delete forms.
  - Dynamically fetches and displays branches from GitHub API when a valid URL is typed.
  - Polls backend every 3 seconds while mining tasks are active.

---

### [client/src/pages/RepositoryAnalytics.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/pages/RepositoryAnalytics.jsx)
- **Role:** Detailed analytics view displaying hotspot treemaps, commit distribution, bus factor, and time-machine filters.
- **Inputs:** Router param `:id` (repository ID), date filter states, commit type filter selection.
- **Outputs:** Renders interactive metrics cards, `HotspotTreemap` component, and orphan risk table.

---

### [client/src/pages/ArchitectureMap.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/pages/ArchitectureMap.jsx)
- **Role:** Visual codebase architectural co-change graph rendered via React Flow.
- **Inputs:** Router param `:id`, API response from `/api/analytics/{id}/temporal-coupling`.
- **Outputs:** Transforms coupling pairs into React Flow nodes/edges and renders interactive zoomable canvas graph.

---

## 🎨 Frontend — Components

### [client/src/components/Layout.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/Layout.jsx)
- **Role:** Application structural layout container (navbar, user profile menu, main content area, footer).
- **Inputs:** React `children` nodes, `user` object.
- **Outputs:** Renders persistent top navigation bar and wrapped page content.

---

### [client/src/components/StatusBadge.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/StatusBadge.jsx)
- **Role:** Visual status indicator badge for repository processing states.
- **Inputs:** `status` string prop (`pending`, `cloning`, `mining`, `ready`, `error`).
- **Outputs:** Renders colored badge with appropriate icon and pulse animation.

---

### [client/src/components/HotspotTreemap.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/HotspotTreemap.jsx)
- **Role:** Interactive Recharts treemap component visualizing file complexity vs change frequency.
- **Inputs:** `data` array prop containing hotspot items (`file_path`, `commits_count`, `total_insertions`, `is_orphan_risk`).
- **Outputs:** Renders custom SVG treemap cells with color gradients, size scaling, and hover tooltips.

---

## 🧪 Test Suites

### [server/tests/test_api_repositories.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/tests/test_api_repositories.py)
- **Role:** Integration tests for repository API routes.
- **Inputs:** Test runner command `python -m unittest discover tests`.
- **Outputs:** Asserts HTTP status codes, URL validation, and repository deletion response schemas.

---

### [server/tests/test_extractor.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/tests/test_extractor.py)
- **Role:** Unit tests for Git extractor service logic.
- **Inputs:** Test git numstat outputs and commit messages.
- **Outputs:** Asserts correct parsing of braced renames, conventional commit classifications, and git log streaming.

---

## 🤖 Phase 5: AI Intelligence (Gemini Integration)

### [server/supabase/migrations/005_ai_cache.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/005_ai_cache.sql)
- **Role:** DDL to create `ai_analysis_cache` table for storing LLM responses.
- **Inputs:** Repository ID, analysis type (`summary`, `shifts`), latest commit SHA, and Gemini response content.
- **Outputs:** Database table with Row Level Security allowing authenticated users to read and the service role to write.

### [server/app/services/ai_service.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/ai_service.py)
- **Role:** Core Gemini integration wrapper.
- **Inputs:** `repo_name`, `aggregated_data` dict (for summaries), commit lists, user questions, and `GEMINI_API_KEY`.
- **Outputs:** Generated text (summaries, chat answers) or structured JSON (architectural shifts) directly from the LLM, tightly formatted without assessment fillers.

### [server/app/routers/ai.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/ai.py)
- **Role:** API endpoints exposing AI services with built-in caching and explicit model routing.
- **Inputs:** `repo_id`, JWT token, and optionally a JSON payload (`AIRequest`) specifying `model` (e.g. `auto`, `gemini_flash`, `groq`). Chat also takes `question`.
- **Outputs:** JSON responses containing `summary`, `shifts`, or `answer`. Handles cache hits/misses. Returns 422 for invalid model choices.

### [client/src/components/AISummaryCard.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/AISummaryCard.jsx)
- **Role:** UI to display the 3-paragraph executive evolution summary.
- **Inputs:** `repoId` prop. User dropdown selection for AI Model.
- **Outputs:** Renders the text summary using `react-markdown` inside a constrained scrollable container, loading skeleton, copy button, and retry/refresh controls.

### [client/src/components/ArchitectureTimeline.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/ArchitectureTimeline.jsx)
- **Role:** UI to display chronologically mapped architectural shifts.
- **Inputs:** `repoId` prop. User dropdown selection for AI Model.
- **Outputs:** Renders a vertical timeline of JSON-derived architecture shifts using `react-markdown` inside a constrained scrollable container, error alerts, copy, and refresh controls.

### [client/src/components/QAChatAssistant.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/QAChatAssistant.jsx)
- **Role:** Interactive ephemeral chat widget for querying repository architecture.
- **Inputs:** `repoId` prop, user input string.
- **Outputs:** Renders a scrollable chat UI with user/assistant bubbles formatted via `react-markdown`, complete with individual copy/regenerate controls and global chat copy.

### [client/src/components/AIDevelopmentStory.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/AIDevelopmentStory.jsx)
- **Role:** UI component that renders a short, narrative retelling of how the repository evolved over time.
- **Inputs:** `repoId` prop. User dropdown selection for AI Model.
- **Outputs:** Renders a non-technical, chronological story using `react-markdown` inside a constrained scrollable container with copy and reload controls.

### [client/src/components/AIAssistanceSignal.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/AIAssistanceSignal.jsx)
- **Role:** Analytical metric card displaying the strength of observable commit patterns associated with AI-assisted development.
- **Inputs:** `repoId` prop.
- **Outputs:** Renders the Signal Score (out of 100 or null handling), confidence level badge, observable signal list, short explanation, and permanent limitation disclaimer.

---

## 🧬 Stage 5 — Evolution Correlation

### [server/app/services/evolution_analyzer.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/evolution_analyzer.py)
- **Role:** Stage 5 deterministic Git/code correlation engine. Produces `repository_events` rows representing historical facts about a repository's evolution.
- **Inputs:**
  - `analyze_evolution(repo_id: str, temp_dir: str, commits: List[Dict], file_diffs: List[Dict])`:
    - `repo_id`: UUID of the repository being analyzed.
    - `temp_dir`: Path to the cloned Git repository on disk. Required for `git show` and `git ls-tree` calls.
    - `commits`: List of commit dicts from `extractor.py` (`id`, `sha`, `committed_at`, `message`, `insertions`, `deletions`).
    - `file_diffs`: List of file diff dicts from `extractor.py` (`commit_id`, `file_path`, `old_path`, `insertions`, `deletions`).
  - `analyze_dependencies_for_commit(repo_dir, commit, file_diffs)`: Sub-function — takes a single commit and its diffs, returns dependency event dicts.
  - `get_commit_parents(repo_dir, sha)`: Returns list of parent SHAs from `git log --format=%P`.
  - `get_file_content_at_commit(repo_dir, sha, file_path)`: Returns file content string via `git show <sha>:<path>`, or `None`.
  - `directory_exists_at_commit(repo_dir, sha, dir_path)`: Returns `True` if directory existed at given commit via `git ls-tree -d`.
- **Outputs / Side Effects:**
  - Writes rows to `repository_events` table via Supabase service-role client.
  - Uses `upsert(on_conflict="repo_id,commit_id,event_type,event_key")` for idempotency.
  - No return value.
- **Event Types Produced:** `dependency_added`, `dependency_removed`, `dependency_version_changed`, `manifest_introduced`, `directory_introduced`, `large_change`, `commit_declared_refactor`.
- **Error Handling:** Malformed manifests are handled gracefully by returning empty dep lists. All git subprocess failures return `None`/`False`/`[]` without raising.

---

### [server/app/routers/evolution.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/evolution.py)
- **Role:** FastAPI router exposing Stage 5 deterministic historical events to the frontend.
- **Prefix:** `/api/repositories/{repo_id}/evolution`
- **Endpoints:**

  #### `GET /events`
  - **Inputs:** `repo_id` (path), `limit` (query, default 100, max 1000), `offset` (query, default 0), `Authorization: Bearer <JWT>` header.
  - **Outputs:** JSON array of `repository_events` rows ordered by `event_date DESC`. Returns raw deterministic evidence — not architectural conclusions.
  - **Auth:** Requires valid Supabase JWT via `get_current_user` dependency. RLS enforces user isolation at DB level.

  #### `GET /files/{file_path:path}`
  - **Inputs:** `repo_id` (path), `file_path` (path parameter, supports slashes), `Authorization: Bearer <JWT>` header.
  - **Outputs:** JSON object containing:
    - `file_path`, `created_at`, `last_modified`, `total_commits`, `total_insertions`, `total_deletions`
    - `history`: List of `{sha, committed_at, author_name, message, insertions, deletions, is_rename, old_path}` entries in chronological order.
  - **Error:** Returns `404` if file is not found in `file_diffs` history.

---

### [server/supabase/migrations/009_evolution_events.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/009_evolution_events.sql)
- **Role:** Database migration for Stage 5. Creates the `repository_events` table.
- **Schema Created:**
  - `repository_events`: `id` (UUID PK), `repo_id` (FK → `repositories`), `commit_id` (nullable FK → `commits`), `event_type` (TEXT), `event_key` (TEXT), `description` (TEXT), `event_date` (TIMESTAMPTZ), `metadata` (JSONB), `created_at` (TIMESTAMPTZ).
- **Constraints:**
  - Unique index: `(repo_id, COALESCE(commit_id, '00000000-...'::uuid), event_type, event_key)` — enforces idempotency.
  - Performance index on `(repo_id, event_date DESC)`.
  - Performance index on `commit_id`.
- **RLS:** `SELECT` policy: users can only access events for repositories they own (via `repositories.user_id = auth.uid()`).
- **No `user_id` column:** Following the pattern established in `008_knowledge_model.sql`, user isolation is achieved via a join to `repositories` rather than denormalizing `user_id` onto this table.

---

## 🏗 Stage 6 — Architecture Evolution Engine

### [server/app/services/phase_analyzer.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/phase_analyzer.py)
- **Role:** Stage 6 deterministic phase-clustering engine. Converts raw `repository_events` from Stage 5 into structured, evidence-backed `architecture_phases`.
- **Constants:**
  - `PHASE_GAP_DAYS = 14` — Configurable inactivity threshold for phase boundary detection.
  - `SIGNIFICANT_EVENT_TYPES` — Set of event types considered architecturally significant: `directory_introduced`, `dependency_added`, `dependency_removed`, `dependency_version_changed`, `manifest_introduced`, `large_change`, `commit_declared_refactor`.
- **Public Entry Point:**
  - `analyze_phases(repo_id: str)` — Loads events, clusters, titles, and persists phases. Idempotent.
- **Internal Functions:**
  - `is_significant_event(event: Dict) -> bool` — Returns `True` if `event["event_type"]` is in `SIGNIFICANT_EVENT_TYPES`.
  - `calculate_days_gap(date1: datetime, date2: datetime) -> float` — Returns absolute gap in days between two datetimes.
  - `cluster_events_into_phases(events: List[Dict]) -> List[List[Dict]]` — Pure function (no DB access). Sorts events chronologically, filters to significant only, splits on gaps > `PHASE_GAP_DAYS`. Returns list of phase buckets.
  - `calculate_phase_metadata(phase_events: List[Dict], phase_index: int) -> Dict` — Returns `{phase_index, start_date, end_date, title, dominant_event_type, event_count}`.
  - `generate_phase_title(phase_events: List[Dict], phase_index: int) -> str` — Deterministic title using priority rule set: (1) recognized framework dependency, (2) recognized technology, (3) dominant directory, (4) dominant event type, (5) generic `"Repository Evolution Phase N"`.
- **Outputs / Side Effects:**
  - Deletes all existing `architecture_phases` for `repo_id` (cascades to `architecture_phase_events`).
  - Inserts new `architecture_phases` rows.
  - Inserts `architecture_phase_events` rows mapping each phase to its source `repository_events`.
  - No return value.
- **Error Handling:** Raises on database errors after logging. Caller (`miner.py`) catches and logs without crashing the overall mining pipeline.

---

### [server/supabase/migrations/011_architecture_phases.sql](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/011_architecture_phases.sql)
- **Role:** Database migration for Stage 6. Creates the `architecture_phases` and `architecture_phase_events` tables.
- **Schema Created:**
  - `architecture_phases`: `id` (UUID PK), `repo_id` (FK → `repositories` ON DELETE CASCADE), `phase_index` (INTEGER), `start_date` (TIMESTAMPTZ), `end_date` (TIMESTAMPTZ), `title` (TEXT), `dominant_event_type` (TEXT), `event_count` (INTEGER), `created_at` (TIMESTAMPTZ).
  - `architecture_phase_events`: `phase_id` (FK → `architecture_phases` ON DELETE CASCADE), `event_id` (FK → `repository_events` ON DELETE CASCADE), composite PK `(phase_id, event_id)`.
- **Constraints:**
  - Unique index: `(repo_id, phase_index)` — enforces ordered, non-duplicate phase numbering per repository.
- **RLS:**
  - `architecture_phases`: `SELECT` policy — users access only phases for repositories they own.
  - `architecture_phase_events`: `SELECT` policy — users access only evidence for phases they own (join through `architecture_phases → repositories`).
- **Cascade behavior:** Deleting a repository cascades to phases; deleting a phase cascades to its evidence mappings.

---

## 🧩 Stage 7 — Evidence Assembler & AI Pipeline

### [server/app/services/evidence_assembler.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/evidence_assembler.py)
- **Role:** Stage 7 Component 1. A strictly deterministic data layer that collects and organizes repository facts from previous stages (1-6) into a centralized `RepositoryEvidence` structure. Contains NO calls to AI or external APIs.
- **Inputs:**
  - `assemble_evidence(repo_id: str, db)`: Takes a repository UUID and a Supabase DB client instance.
- **Outputs / Side Effects:**
  - Returns a `RepositoryEvidence` dictionary object.
  - Dict contains keys: `repository` (metadata), `technology` (deduplicated fingerprint), `phases` (Stage 6 architecture phases + mapped events), `hotspots` (top 10 active files), `contributors` (commit stats + 80% bus factor), and `commit_sample` (top significant commits by 2σ percentile rank).
  - Purely read-only; no database mutations.
- **Error Handling:** Propagates underlying database exceptions. Missing optional data returns empty lists/dicts rather than raising errors.

---

### Stage 6 → Stage 7 Data Contract (via `routers/ai.py` `/shifts` endpoint)

- **What Stage 6 provides to Stage 7:**
  - `architecture_phases`: `{title, start_date, end_date, dominant_event_type}` per phase.
  - `architecture_phase_events JOIN repository_events`: `{event_type, event_key, event_date, metadata}` per evidence item.
- **Format delivered to LLM (via `ai_service.detect_architecture_shifts`):**
  ```json
  [
    {
      "phase": {
        "title": "FastAPI Backend Foundation",
        "start_date": "2026-01-20T00:00:00Z",
        "end_date": "2026-01-20T00:00:00Z",
        "dominant_event_type": "dependency_added"
      },
      "evidence": [
        {"type": "dependency_added", "name": "dependency:requirements.txt:fastapi", "date": "...", "metadata": {...}},
        {"type": "directory_introduced", "name": "directory:server/app", "date": "...", "metadata": {...}}
      ]
    }
  ]
  ```
- **LLM's role:** Synthesize phases into a readable narrative. LLM does NOT determine phase boundaries.


