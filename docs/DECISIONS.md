# Architectural Decisions & Technical Trade-offs Log (`DECISIONS.md`)

> **Location:** `docs/DECISIONS.md`  
> **Purpose:** Document all technical, architectural, and library choices made in **GitCompass**, along with their rationale, alternative options evaluated, and accepted trade-offs.

---

## 📌 Standard Operating Procedure for Engineers & AI Agents

Whenever modifying, refactoring, or introducing new code/libraries to GitCompass:
1. **Document the Decision:** Add an entry under [Recent Decisions & Active Trade-offs](#recent-decisions--active-trade-offs) using the standard format.
2. **Explain the Why:** Explicitly note why library/pattern X was chosen over library/pattern Y.
3. **Record Trade-offs:** Be explicit about what performance, complexity, or maintenance trade-offs were accepted.

---

## 📋 Standard Decision Entry Template

```markdown
### [YYYY-MM-DD] - <Short Decision Title>

- **Context / Problem:** What feature or issue required a decision?
- **Options Considered:**
  1. Option A (e.g., Library X)
  2. Option B (e.g., Custom implementation Y)
- **Decision:** Selected Option A.
- **Rationale:** Why was this option superior in our specific context?
- **Trade-offs Accepted:** What are the downsides or constraints we accept by making this choice?
- **Affected Files / Flow:** Links to affected files or execution paths in `docs/FLOW.md`.
```

---

## 🏛 Historical Architectural Decisions

### [2026-08-10] - Technology Stack Selection (FastAPI + React Vite + Supabase)

- **Context / Problem:** Establishing the baseline full-stack architecture for Git Compass to analyze Git histories and visualize codebase evolution.
- **Options Considered:**
  1. **Full-stack Next.js (Node.js backend):** Unified JavaScript repository, but limited native support and performance for heavy Git operations / Python data science libraries.
  2. **FastAPI (Python) + React (Vite) + Supabase (PostgreSQL/Auth):** Decoupled micro-architecture separating async Git processing from UI presentation.
- **Decision:** Selected Option 2 (FastAPI + React Vite + Supabase).
- **Rationale:**
  - **FastAPI:** Python offers unmatched capabilities for Git history mining (`GitPython`, subprocess processing, data structures). FastAPI provides fast async I/O, OpenAPI docs, and Pydantic validation.
  - **React (Vite):** Extremely fast HMR during development, clean single-page app (SPA) routing with `react-router-dom`, and lightweight distribution.
  - **Supabase:** Provides instant GitHub OAuth integration, managed PostgreSQL, Row-Level Security (RLS) for tenant isolation, and custom SQL RPCs for analytical queries.
- **Trade-offs Accepted:**
  - Managing two runtime environments (Python backend + Node frontend).
  - Cross-service JWT token validation standard required on backend routes.

---

### [2026-08-10] - Local Repository Mining Strategy (Git Cloning vs. GitHub REST/GraphQL API)

- **Context / Problem:** Extracting deep commit logs, file diffs, line additions/deletions, and file coupling metrics across thousands of historical commits.
- **Options Considered:**
  1. **GitHub REST / GraphQL API:** Fetching commit histories over HTTP.
  2. **Local Git Cloning (`GitPython` / subprocess):** Shallow/full cloning repository locally to inspect commit trees directly.
- **Decision:** Selected Option 2 (Local Git Cloning).
- **Rationale:**
  - GitHub REST/GraphQL APIs enforce strict rate limits (5,000 requests/hour) and require many network round-trips to reconstruct full diff trees for large repositories.
  - Local Git cloning allows instant line-by-line diff extraction (`git log --numstat`), operates offline/uncapped after clone, and processes thousands of commits in seconds.
- **Trade-offs Accepted:**
  - Requires transient disk space on server for repository storage (`/tmp` or transient directory).
  - Cloning large repositories incurs initial network load before mining starts.

---

### [2026-08-10] - Visualization Layer (React Flow & Recharts vs. D3.js)

- **Context / Problem:** Rendering complex codebase architecture maps (file node graphs, directory modules) and analytical charts (hotspot treemaps, churn over time).
- **Options Considered:**
  1. **Raw D3.js:** Maximum visualization freedom, but requires direct DOM manipulation and heavy custom React lifecycle integration.
  2. **React Flow + Recharts:** React-native declarative canvas node graph engine (`React Flow`) paired with declarative SVG charting (`Recharts`).
- **Decision:** Selected Option 2 (`React Flow` + `Recharts`).
- **Rationale:**
  - `React Flow` handles node dragging, zooming, panning, layout management, and custom edge connections seamlessly within React's declarative state lifecycle.
  - `Recharts` integrates seamlessly with React state for responsive treemaps and time-series graphs without custom canvas manipulation code.
- **Alternatives Evaluated:**
  - Raw D3.js: Too low-level, high learning curve.
  - Vis.js / Sigma.js: Good for networks, but React Flow is better integrated with the React ecosystem and offers superior DX for custom nodes.
- **Trade-offs Accepted:**
  - React Flow nodes require explicit coordinate management or an auto-layout engine (dagre/elkjs) to prevent overlapping in large graphs.
  - Performance may degrade with >1000 simultaneous nodes (React Flow limits), necessitating grouping/clustering heuristics for massive codebases.

---

### [2026-08-10] - Phase 5 AI Intelligence Layer (Gemini Integration)
- **Decision:** Use Google's `google-genai` SDK and the Gemini 2.5 Flash model for generating codebase summaries, architecture shifts, and conversational Q&A.
- **Context/Rationale:** We needed an LLM layer capable of semantic reasoning over historical data. Gemini provides a large context window and strong reasoning capabilities.
- **Alternatives Evaluated:** OpenAI (GPT-4o), Anthropic (Claude 3.5 Sonnet). Gemini was chosen based on current requirements and SDK availability.
- **Trade-offs Accepted:**
  - **Token Limits/Cost:** Passing full commit logs to LLMs is expensive. We accepted a hard limit: architecture shift detection is disabled for repos with >500 commits to control costs and latency.
  - **Caching:** Added a Supabase table (`ai_analysis_cache`) to cache LLM responses instead of generating on-the-fly every time.
  - **Chat Persistence:** Q&A chat is currently ephemeral (session-based) rather than persisted in the database to reduce immediate complexity.

---

### [2026-08-11] - Phase 6 Multi-Provider AI Fallback & Task-Aware Routing
- **Context / Problem:** Gemini API calls can fail due to rate limits (HTTP 429) or quota exhaustion. Additionally, using full Gemini 3.5 Flash for simple tasks wastes quota. We need task-aware routing to conserve quota, and a fallback chain to maximize uptime.
- **Options Considered:**
  1. **Single Model / Single Provider:** Use Gemini 3.5 Flash for everything and fail hard on quota limits.
  2. **Task-Aware Gemini + Multi-Provider Fallback:** Route simple tasks to `gemini-3.5-flash-lite` and complex tasks to `gemini-3.5-flash`. If the selected Gemini model fails due to a qualifying provider error, fall back to Groq (`llama-3.3-70b-versatile`), and then to a local Ollama model (`gemma3:12b`/`gemma3:4b`).
- **Decision:** Implement Option 2 (Task-Aware Gemini Routing + 3-Tier Fallback Chain).
- **Rationale:**
  - **Task-Aware Routing:** `generate_evolution_summary` and `answer_qa` use Flash Lite (high volume, straightforward interpretation). `generate_development_story` and `detect_architecture_shifts` use full Flash (complex reasoning, chronological narrative).
  - **Gemini (Primary):** Highest priority. The selected model is always attempted first for every independent request.
  - **Groq (Secondary):** Extremely fast cloud inference. Activated only if the primary Gemini model encounters a qualifying failure (429, quota, 503).
  - **Ollama (Tertiary):** Local GPU inference. Config-driven (`OLLAMA_ENABLED=false` by default). Activated only if both Gemini and Groq fail/are unconfigured.
  - **Provider Abstraction:** The frontend remains provider-agnostic. `ai_service.py` coordinates model selection and fallback execution.
- **Trade-offs Accepted:**
  - Requires maintaining mapping of tasks to Gemini models in backend configuration.
  - Fallback errors must be strictly distinguished from feature-level parsing errors (e.g., malformed JSON raises `ValueError` immediately without fallback).

---

### [2026-08-10] - API Communication Protocol (Vite Dev Server Proxy vs. CORS headers)

- **Context / Problem:** Handling API calls between frontend (`http://localhost:5173`) and backend (`http://localhost:8000`) during local development.
- **Options Considered:**
  1. **FastAPI CORS Middleware:** Exposing headers for cross-origin requests.
  2. **Vite Development Proxy:** Proxying requests originating from `/api/*` on port 5173 to `http://localhost:8000`.
- **Decision:** Selected Option 2 (Vite Proxy).
- **Rationale:**
  - Prevents CORS pre-flight precheck overhead during development.
  - Simplifies authentication security model (cookies/headers appear same-origin to browser).
- **Trade-offs Accepted:**
  - Production deployments require explicit CORS configuration or unified ingress proxy (e.g., NGINX / Cloudflare).

---

## 📝 Recent Decisions & Active Trade-offs

### [2026-08-11] - AI Prompt Optimization (Backend Aggregation vs. LLM Calculation)
- **Context / Problem:** Passing raw lists of files, commits, and ownership data to the Gemini model in `routers/ai.py` caused high token usage and led to the model "hallucinating" subjective assessments rather than reporting factual data.
- **Options Considered:**
  1. Have Gemini process raw lists and do the math (high token usage).
  2. Aggregate all metrics on the FastAPI backend and pass a tightly packed JSON object to the model.
- **Decision:** Selected Option 2 (Backend Aggregation).
- **Rationale:** Moving calculations like Top Authors, Total Files, and Churn to the Python backend drastically reduces the input token payload. Sending a strictly structured JSON object (via `json.dumps(..., separators=(',', ':'))`) removes unnecessary whitespace and gives the LLM clear, objective data to summarize. Prompt instructions were rewritten to strictly ban subjective assessment and prescriptive language.
- **Trade-offs Accepted:** Adds slightly more data wrangling logic into `routers/ai.py`, decoupling the AI's "analytical" capability from raw text parsing, but results in much cheaper, faster, and more deterministic AI responses.
- **Affected Files / Flow:** `server/app/routers/ai.py`, `server/app/services/ai_service.py`.

### [2026-08-11] - AI Insights Enhancements: Development Story & AI-Assistance Signal Score
- **Context / Problem:** Users requested a narrative retelling of repository history (Development Story) and an evidence-based pattern evaluation rather than an arbitrary "AI Likelihood" percentage meter. Additionally, the chat assistant consumed valuable layout space in the analytics grid.
- **Decision:**
  1. Implemented **Development Story** (`/api/ai/story`) using month-by-month chronological backend aggregation.
  2. Overhauled "AI Likelihood" into **AI-Assistance Signal Score** (`/api/ai/signals`). Calculated entropy metrics natively in Python (repetition %, median insertions, burst frequency) and passed them to Gemini to output a score (out of 100 or null), confidence level, concrete signals array, and permanent disclaimer. Enforced minimum-data validation (< 5 commits returns `score: null`).
  3. Converted `QAChatAssistant` from an inline card into a global floating chatbot widget with fixed bottom-right positioning (`position: fixed`).
- **Rationale:** Minimizes token usage via Python-side metric pre-calculation and monthly aggregation. Ensures AI cannot hallucinate non-existent phases or claim absolute proof of AI authorship. Moving chat to a FAB optimizes screen real estate.
- **Affected Files / Flow:** `server/app/routers/ai.py`, `server/app/services/ai_service.py`, `client/src/components/AIDevelopmentStory.jsx`, `client/src/components/AIAssistanceSignal.jsx`, `client/src/components/QAChatAssistant.jsx`, `client/src/pages/RepositoryAnalytics.jsx`.

### [2026-08-12] - Docker Containerization & Redis Infrastructure Setup
- **Context / Problem:** Needed a robust caching & task queue infrastructure for GitCompass. Installing Redis locally on host machines introduces environment dependencies and setup friction.
- **Options Considered:**
  1. Local Redis installation on host OS / WSL2 directly.
  2. Docker Compose containerization for FastAPI (`server`) and Redis (`redis:7-alpine`).
- **Decision:** Selected Option 2 (Docker Compose containerization).
- **Rationale:**
  - Docker Compose provides reproducible, isolated development and production environments across platforms.
  - The FastAPI server container connects to Redis seamlessly using Docker network service name `redis:6379`.
  - `.dockerignore` optimizes build context from ~57.54 MB to ~3.19 kB by excluding `.env`, `.venv`, `.git`, `__pycache__`, etc.
  - Secrets are securely injected into containers at runtime via `env_file` (`server/.env`).
- **Trade-offs Accepted:**
  - Container changes require `docker compose up -d --build` when new local modules or dependencies are added to rebuild container image context.
- **Affected Files / Flow:** [docker-compose.yml](file:///c:/Users/mulla/Desktop/Projects/GitCompass/docker-compose.yml), [Dockerfile](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/Dockerfile), [.dockerignore](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/.dockerignore), [redis.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/core/redis.py).

### [2026-08-13] - Explicit AI Model Selection and Component Layout Constraints
- **Context / Problem:** Users wanted the ability to explicitly choose which LLM (Gemini Flash, Gemini Flash Lite, Groq Llama 3) powers each individual AI insights card. Additionally, the CSS grid on the analytics page overflowed and pushed content down infinitely due to unconstrained markdown rendering.
- **Decision:** 
  1. Exposed model selection explicitly via frontend dropdowns. 
  2. Implemented strict endpoint payload validation via `AIModelChoice` Enum on the FastAPI routes.
  3. Preserved fallback semantics by dynamically injecting the requested model into the start of the existing `build_provider_chain` mechanism (Groq fallback remains active for Gemini models).
  4. Fixed the UI overflow by applying localized `.overflow-y-auto` scroll containers and max-height boundaries onto the child AI React components (`AISummaryCard`, `AIDevelopmentStory`, `ArchitectureTimeline`) rather than hacking the parent Grid layout.
- **Rationale:** Strict Enum validation (`auto`, `gemini_flash`, `gemini_flash_lite`, `groq`) ensures invalid models never reach the LLM SDK. Constraining the React components internally creates a consistent, scrollable widget interface without breaking the overarching responsive dashboard grid.
- **Trade-offs Accepted:** The `generate_ai_response` and its parent features (`generate_evolution_summary`, etc.) now pass the `selected_model` parameter all the way down, slightly widening the function signatures.
- **Affected Files / Flow:** `server/app/routers/ai.py`, `server/app/services/ai_service.py`, `client/src/lib/api.js`, `client/src/components/AISummaryCard.jsx`, `client/src/components/AIDevelopmentStory.jsx`.

### [2026-08-13] - Explicit Supabase API Role Grants for Local Development
- **Context / Problem:** When using `supabase start` and applying custom SQL migrations containing standard `CREATE TABLE` commands, the local database does not automatically grant `SELECT`, `INSERT`, `UPDATE`, and `DELETE` privileges to the `anon`, `authenticated`, and `service_role` API roles. This is because the local default ACLs (`pg_default_acl`) only grant `TRUNCATE`, `REFERENCES`, and `TRIGGER` to these roles.
- **Options Considered:**
  1. Manually run a one-time `GRANT` query directly against the local Postgres database.
  2. Create a new idempotent migration file to explicitly grant the necessary privileges.
- **Decision:** Selected Option 2 (explicit migration `007_api_role_grants.sql`).
- **Rationale:** Ensures that the local development environment remains reproducible via `supabase db reset`. Relies on explicit SQL DCL (Data Control Language) rather than undocumented/implicit Supabase Studio UI behavior.
- **Trade-offs Accepted:** Adds boilerplate `GRANT` and `ALTER DEFAULT PRIVILEGES` commands as a permanent migration step.
- **Affected Files / Flow:** `server/supabase/migrations/007_api_role_grants.sql`

### [2026-08-13] - Supabase Local Development via CLI vs. Main Docker Compose
- **Context / Problem:** GitCompass requires a PostgreSQL database with Row-Level Security, an Auth service (GoTrue), and a REST API (PostgREST). We evaluated whether to integrate the open-source Supabase Docker image stack directly into our primary `docker-compose.yml` or use the official `supabase-cli`.
- **Options Considered:**
  1. Add Postgres, GoTrue, and PostgREST manually to `docker-compose.yml`.
  2. Use `supabase start` to run the official local Supabase container stack independently.
- **Decision:** Selected Option 2 (Supabase CLI).
- **Rationale:** The Supabase local stack consists of ~10 interconnected microservices (Kong, GoTrue, Studio, Vector, PostgREST, etc.). Managing these manually within our primary `docker-compose.yml` adds immense maintenance overhead. By keeping it separate, our `docker-compose.yml` remains clean (FastAPI + Redis only) while the Supabase CLI handles database resets, migrations, and Auth/API parity with production via `.toml` configuration.
- **Trade-offs Accepted:** Requires running two independent daemon commands during local development (`supabase start` and `docker compose up`).
- **Affected Files / Flow:** `server/supabase/config.toml`, `README.md`

---

### [2026-08-21] - Stage 5: git show for Historical Dependency Comparison

- **Context / Problem:** Stage 5 needs to detect `dependency_added`, `dependency_removed`, and `dependency_version_changed` events from Git history. The naive approach would only flag "manifest file was modified" without knowing what actually changed.
- **Options Considered:**
  1. Store historical manifest snapshots in the database for comparison.
  2. Use `git show <commit>:<path>` and `git show <parent>:<path>` within the cloned `temp_dir` to retrieve and parse manifests at each commit.
- **Decision:** Selected Option 2 (`git show` within `temp_dir`).
- **Rationale:** Git is the historical source of truth. Storing historical manifest snapshots in the database would duplicate data already in the Git object store, add schema complexity, and create a secondary source of truth. `git show` is deterministic and always accurate. The `temp_dir` is available during Stage 5 execution.
- **Trade-offs Accepted:** Stage 5 must run before `safe_cleanup_dir(temp_dir)` is called. If `temp_dir` is cleaned up prematurely, `git show` would fail. This is enforced by placement in `miner.py`.
- **Affected Files / Flow:** [`evolution_analyzer.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/evolution_analyzer.py), [`miner.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/miner.py)

---

### [2026-08-21] - Stage 5: Deterministic event_key for Idempotency

- **Context / Problem:** Stage 5 analysis can be re-run on the same repository (full re-mine or incremental sync overlap). We needed a strategy to prevent duplicate `repository_events` rows.
- **Options Considered:**
  1. Use `md5(metadata::text)` as part of the uniqueness constraint. Simple but fragile — JSON key ordering is not guaranteed and would produce different hashes for semantically identical events.
  2. Add an explicit, deterministic `event_key` column with a composite `UNIQUE(repo_id, commit_id, event_type, event_key)` constraint. Use structured string keys such as `dependency:path:name` or `directory:src/auth`.
- **Decision:** Selected Option 2 (explicit `event_key` column).
- **Rationale:** `event_key` produces a stable, human-readable identity for each event that is independent of JSON serialization order. The composite unique index enforces deduplication at the database level. `upsert(..., on_conflict=...)` on the Supabase client handles graceful idempotent writes.
- **Trade-offs Accepted:** Event key construction must be consistent across runs. If `event_key` construction logic changes in the future, old events will not be de-duplicated against new ones.
- **Affected Files / Flow:** [`009_evolution_events.sql`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/009_evolution_events.sql), [`evolution_analyzer.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/evolution_analyzer.py)

---

### [2026-08-21] - Stage 5: Mean + 2σ Threshold for large_change Detection

- **Context / Problem:** Stage 5 must classify commits with unusually high churn as `large_change` events. The threshold must be deterministic and repository-relative, not a hardcoded line count.
- **Options Considered:**
  1. Hardcoded threshold (e.g., `> 1000 lines`). Simple, but meaningless across repositories of very different sizes.
  2. 95th-percentile outlier. Percentile requires sorting — accurate but labelled as potential proof of refactoring in the earlier rejected plan.
  3. Mean + 2 standard deviations (µ + 2σ). Standard statistical outlier detection. Captures the top ~2.3% of commits by churn, relative to the repository's own baseline. Floor of 500 lines prevents false positives on tiny repositories.
- **Decision:** Selected Option 3 (µ + 2σ with a minimum floor of 500).
- **Rationale:** µ + 2σ is a widely accepted, self-calibrating outlier rule. It is computed solely from the commits in the analyzed range and carries no interpretive weight — it is a statistical fact, not an architectural conclusion. The floor prevents every commit in a 5-commit repo from being flagged.
- **Trade-offs Accepted:** If a repository has extremely high variance (e.g., one massive initial commit and then tiny fixes), the threshold will be very high and may miss some genuinely large commits. Stage 6 can apply additional interpretation if needed.
- **Affected Files / Flow:** [`evolution_analyzer.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/evolution_analyzer.py)

---

### [2026-08-21] - Stage 5: Strict Stage 5 / Stage 6 Boundary

- **Context / Problem:** Early Stage 5 design drafts included logic that would infer architectural intent (e.g., "authentication subsystem introduced", "major refactor detected"). This violates the separation of extraction and reasoning described in `PHASE_PLAN.md`.
- **Decision:** Stage 5 is strictly limited to deterministic historical facts. Stage 6 remains responsible for interpreting those facts.
- **Rationale:** Mixing deterministic evidence with AI-inferred interpretation at the extraction layer would make the Repository Knowledge Model unreliable as an input to Stage 7 (AI Reasoning Layer). Facts must be cleanly separated from inferences.
- **Trade-offs Accepted:** Stage 5 events will appear "raw" to the frontend without high-level labels. This is intentional — Stage 6 will provide those labels from the deterministic evidence.
- **Affected Files / Flow:** [`evolution_analyzer.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/evolution_analyzer.py), `docs/PHASE_PLAN.md`

---

### [2026-08-21] - Stage 6: Time-Gap Clustering for Phase Grouping

- **Context / Problem:** Stage 6 must group raw `repository_events` from Stage 5 into coherent architectural phases without any LLM involvement. We needed a deterministic, configurable algorithm that produces stable groupings regardless of how many times it runs.
- **Options Considered:**
  1. **Fixed number of phases (k-means):** Partition events into a fixed `k` number of groups. But k is not known in advance per repository and the algorithm introduces non-determinism from seed initialization.
  2. **Commit-message clustering:** Group events by keywords in commit messages. Fragile, depends on developer conventions, and violates the determinism constraint.
  3. **Time-gap clustering with configurable threshold (`PHASE_GAP_DAYS`):** Sort significant events chronologically; start a new phase when the gap between consecutive significant events exceeds the threshold. Fully deterministic, configurable, and self-calibrating.
- **Decision:** Selected Option 3 (time-gap clustering with `PHASE_GAP_DAYS = 14`).
- **Rationale:** The 14-day rule is based on typical sprint/release cadence. It is self-calibrating, configurable via one constant, and produces zero ambiguity on ties (gap ≤ 14 days = same phase; gap > 14 days = new phase).
- **Trade-offs Accepted:** A repository with continuous daily commits will produce a single large phase. This is intentional — no architectural boundary has occurred. The threshold can be tuned via `PHASE_GAP_DAYS`.
- **Affected Files / Flow:** [`phase_analyzer.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/phase_analyzer.py)

---

### [2026-08-21] - Stage 6: Deterministic Title Generation Without LLM

- **Context / Problem:** Each architectural phase needs a human-readable title (e.g., "FastAPI Backend Foundation"). Using an LLM would violate the Stage 6 determinism constraint and introduce latency/cost during the mining pipeline.
- **Options Considered:**
  1. Use the LLM to generate a title for each phase. Violates the core constraint — no LLM in Stage 6.
  2. Use only the dominant event type as the title. Too generic and not useful.
  3. A priority-ordered heuristic rule set: (1) recognized framework/dependency name, (2) recognized technology, (3) dominant directory, (4) dominant event type, (5) generic fallback.
- **Decision:** Selected Option 3 (priority-ordered heuristic rule set).
- **Rationale:** The title generator runs in microseconds with zero external dependencies. It is fully reproducible — identical events always produce identical titles. The vocabulary is intentionally limited and explicit, avoiding hallucination risk.
- **Trade-offs Accepted:** The vocabulary is bounded. Frameworks not in the heuristic set fall through to the directory or generic title. The vocabulary can be expanded incrementally.
- **Affected Files / Flow:** [`phase_analyzer.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/phase_analyzer.py) → `generate_phase_title()`

---

### [2026-08-21] - Stage 6: Idempotency via Delete-Before-Insert

- **Context / Problem:** `analyze_phases(repo_id)` is invoked each time a repository is mined. Naively appending new phases would accumulate duplicates.
- **Options Considered:**
  1. Upsert on `(repo_id, phase_index)`. Risky — if the number of phases changes between runs, stale phases from prior runs remain.
  2. Delete all existing `architecture_phases` for the repo before inserting. Clean slate combined with cascading FKs on `architecture_phase_events` atomically removes all stale evidence mappings.
- **Decision:** Selected Option 2 (delete-before-insert with cascading FK cleanup).
- **Rationale:** A single `DELETE WHERE repo_id = ...` atomically purges all stale phase/evidence data via cascade. Simpler and safer than upsert logic handling variable-length phase arrays.
- **Trade-offs Accepted:** Brief window between delete and insert where no phases exist. Invisible to end users since reads go through the REST API, not the mining worker.
- **Affected Files / Flow:** [`phase_analyzer.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/phase_analyzer.py) → `analyze_phases()`, [`011_architecture_phases.sql`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/supabase/migrations/011_architecture_phases.sql)

---

### [2026-08-21] - Stage 7: `/shifts` Now Consumes Deterministic Phase Evidence

- **Context / Problem:** The previous `/shifts` endpoint fed up to 200 raw commit messages to the LLM and asked it to infer architectural phases. The LLM was determining phase boundaries — a Stage 6 responsibility — and was prone to hallucinating dates or conflating unrelated changes.
- **Options Considered:**
  1. Keep feeding raw commits with a stronger system prompt. Unreliable — the LLM cannot ignore raw commits even if instructed.
  2. Feed deterministic Stage 6 phase data (titles, dates, dominant event type, evidence events) to the LLM and ask it only to synthesize a human-readable narrative.
- **Decision:** Selected Option 2 (LLM receives deterministic phase JSON as input).
- **Rationale:** Enforces the GitCompass principle: Stage 6 answers *what happened and when*; Stage 7 answers *what it means*. The LLM cannot hallucinate phase boundaries because they are provided as structured JSON facts.
- **Trade-offs Accepted:** If a repository has zero `architecture_phases` (mined before Stage 6 was run), `/shifts` returns an error prompting re-mining.
- **Affected Files / Flow:** [`routers/ai.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/ai.py), [`services/ai_service.py`](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/ai_service.py)
### [2026-08-21] - Stage 7: Centralized Deterministic Evidence Assembler

- **Context / Problem:** Stage 7 AI reasoning features (Development Story, Architecture Timeline, AI Summary) previously fetched raw database records independently. This caused code duplication, led to N+1 queries, and hit URL length limits when generating evidence dynamically in the router.
- **Options Considered:**
  1. Have each AI feature construct its own context and evidence gathering logic.
  2. Build a centralized, purely deterministic `EvidenceAssembler` that builds a single `RepositoryEvidence` object containing all required context (phases, hotspots, commit samples, technology).
- **Decision:** Selected Option 2 (Centralized `EvidenceAssembler`).
- **Rationale:** A single deterministic gathering layer eliminates code duplication, enables heavy optimization (avoiding N+1 queries by querying by `repo_id` and grouping in memory), and provides the LLM with a single unified data shape to reason over. The assembler is strictly deterministic—no LLM calls happen during assembly.
- **Trade-offs Accepted:** Adds a heavy data aggregation step prior to LLM execution. To avoid memory bloat and "URI too long" errors, limits are placed on hotspots (top 10), contributors (top 5), and commit samples (top 30), relying on statistical percentile ranking rather than full histories.
- **Affected Files / Flow:** `server/app/services/evidence_assembler.py`, `server/verify_evidence.py`



