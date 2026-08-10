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
