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
- **Role:** API endpoints exposing AI services with built-in caching.
- **Inputs:** `repo_id`, JWT token, and optionally a JSON payload for chat questions (`question`).
- **Outputs:** JSON responses containing `summary`, `shifts`, or `answer`. Handles cache hits/misses.

### [client/src/components/AISummaryCard.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/AISummaryCard.jsx)
- **Role:** UI to display the 3-paragraph executive evolution summary.
- **Inputs:** `repoId` prop.
- **Outputs:** Renders the text summary using `react-markdown`, loading skeleton, copy button, and retry/refresh controls.

### [client/src/components/ArchitectureTimeline.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/ArchitectureTimeline.jsx)
- **Role:** UI to display chronologically mapped architectural shifts.
- **Inputs:** `repoId` prop.
- **Outputs:** Renders a vertical timeline of JSON-derived architecture shifts using `react-markdown`, error alerts (e.g. if commits > 500), copy, and refresh controls.

### [client/src/components/QAChatAssistant.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/QAChatAssistant.jsx)
- **Role:** Interactive ephemeral chat widget for querying repository architecture.
- **Inputs:** `repoId` prop, user input string.
- **Outputs:** Renders a scrollable chat UI with user/assistant bubbles formatted via `react-markdown`, complete with individual copy/regenerate controls and global chat copy.

### [client/src/components/AIVibeMeter.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/components/AIVibeMeter.jsx)
- **Role:** Visual indicator showing the likelihood percentage that the repository was AI-generated based on commit entropy / patterns.
- **Inputs:** `repoId` prop.
- **Outputs:** Renders a sleek progress bar meter with 25%, 50%, and 75% visual markers.
