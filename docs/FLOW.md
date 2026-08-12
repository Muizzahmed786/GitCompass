# System Execution Flow (`FLOW.md`)

> **Location:** `docs/FLOW.md`  
> **Purpose:** Document how execution travels across files, modules, functions, and database layers in **GitCompass**. Tracks call chains, request lifecycles, and the current active execution path being modified.

---

## 🗺 System Architecture & Module Map

```
┌────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (React / Vite)                         │
│                                                                        │
│   App.jsx (Auth Routing)                                               │
│    ├── Login.jsx                 ───▶ Supabase OAuth (GitHub)          │
│    └── Layout.jsx                                                      │
│         ├── Dashboard.jsx            ───▶ Add Repo / Status Polling    │
│         ├── RepositoryAnalytics.jsx  ───▶ Hotspot Treemaps & Metrics   │
│         └── ArchitectureMap.jsx      ───▶ React Flow Graph             │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ HTTP REST (/api/* via Vite Proxy)
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                           SERVER (FastAPI)                             │
│                                                                        │
│   main.py (App & Router Mounting)                                      │
│    ├── dependencies.py (JWT Validation via Supabase / PyJWT)          │
│    ├── routers/                                                        │
│    │    ├── health.py                                                  │
│    │    ├── repositories.py                                            │
│    │    └── analytics.py                                               │
│    └── services/                                                       │
│         ├── cloner.py     ───▶ Git subprocess / local clone           │
│         ├── extractor.py  ───▶ Git log parsing & diff calculation     │
│         └── miner.py      ───▶ Async Background Worker Task           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │ Database Requests / SQL RPCs
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        DATABASE (Supabase PostgreSQL)                  │
│                                                                        │
│   Tables: profiles | repositories | commits | file_diffs               │
│   RPC Functions: get_hotspots | get_churn_timeline | get_file_coupling│
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🔁 Detailed Execution Flows

### 1. Authentication & Session Lifespan Flow

```
[User] ──(Click "Continue with GitHub")──▶ client/src/pages/Login.jsx
                                                    │
                                                    ▼
                                     client/src/lib/supabase.js
                                                    │
                                       (supabase.auth.signInWithOAuth)
                                                    │
                                                    ▼
                                           GitHub OAuth Provider
                                                    │
                                         (Redirect back with code)
                                                    │
                                                    ▼
client/src/App.jsx ◀──(onAuthStateChange)── Supabase Auth Client
       │
       ├── Session Active? ──▶ Renders <Layout><Routes... /></Layout>
       └── Session Null?   ──▶ Renders <Login />
```

**Call Sequence:**
1. [Login.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/pages/Login.jsx) calls `supabase.auth.signInWithOAuth({ provider: 'github' })`.
2. Browser redirects to GitHub auth -> Supabase handles OAuth handshake -> returns session tokens stored in local storage.
3. [App.jsx](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/App.jsx) registers `supabase.auth.onAuthStateChange` listener on mount.
4. When token is loaded/refreshed, `setSession(session)` triggers React state update, making JWT available to all API calls.

---

### 2. Repository Addition & Mining Engine Execution Flow

```
[User] ──(Input URL & Submit)──▶ client/src/pages/Dashboard.jsx
                                          │
                                          ▼ (POST /api/repositories)
                               client/src/lib/api.js (Attach Auth Header)
                                          │
                                          ▼
                         server/app/routers/repositories.py
                                          │
                        (dependencies.get_current_user)
                                          │
                                          ▼
                         server/app/database.py (Get Supabase client)
                                          │
                         (Insert record with status='pending')
                                          │
               (fastapi.BackgroundTasks.add_task)
                                          │
                                          ▼
                          server/app/services/miner.py
                            (mine_repository_background)
                                     │        │
                   ┌─────────────────┘        └──────────────────┐
                   ▼                                             ▼
     server/app/services/cloner.py               server/app/services/extractor.py
     (clone_or_fetch_repo)                       (extract_commits_and_diffs)
             │                                                   │
             ▼                                                   ▼
   Executes `git clone`                         Parses `git log --numstat`
   Updates status='cloning'                     Updates status='mining'
                                                Batch inserts `commits` & `file_diffs`
                                                Updates status='ready'
```

**Call Sequence:**
1. **Frontend Request:** `Dashboard.jsx` calls `api.post('/api/repositories', { url })`.
2. **HTTP Client:** [api.js](file:///c:/Users/mulla/Desktop/Projects/GitCompass/client/src/lib/api.js) fetches session JWT from Supabase client and sets `Authorization: Bearer <token>`.
3. **Backend Router:** [repositories.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/repositories.py) validates authorization token via [dependencies.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/dependencies.py).
4. **Database Record Creation:** Initial repository record created in Supabase with status `pending`.
5. **Background Dispatch:** FastAPI `BackgroundTasks` executes `mine_repository_background(repo_id)` in [miner.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/miner.py).
6. **Cloning Step:** [miner.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/miner.py) calls [cloner.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/cloner.py) `clone_or_fetch_repo()`. Repo is cloned into transient storage; DB status set to `cloning`.
7. **Extraction Step:** [miner.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/miner.py) calls [extractor.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/services/extractor.py) `extract_commits_and_diffs()`. `extractor.py` executes `git log` commands to parse commit metadata and line churn (`+lines`, `-lines`).
8. **Batch Persistence:** Commit records and file diffs are written to Supabase `commits` and `file_diffs` tables. Repository status updated to `ready`.
9. **UI Polling:** `Dashboard.jsx` polls `GET /api/repositories` every 3s to update status badge from `Pending` -> `Cloning` -> `Mining` -> `Ready`.

---

### 3. Analytics & Hotspot Data Flow

```
[User] ──(Select Repo)──▶ client/src/pages/RepositoryAnalytics.jsx
                                      │
                                      ▼ (GET /api/analytics/{id}/hotspots)
                            server/app/routers/analytics.py
                                      │
                                      ▼
                            server/app/database.py
                                      │
                         (rpc('get_hotspots', params))
                                      │
                                      ▼
                           Supabase Database Engine
                                      │
                             (Returns JSON Array)
                                      │
                                      ▼
            client/src/components/HotspotTreemap.jsx (Renders Recharts)
```

**Call Sequence:**
1. **Frontend Mounting:** `RepositoryAnalytics.jsx` mounts and requests analytics endpoints:
   - `GET /api/analytics/{id}/summary`
   - `GET /api/analytics/{id}/hotspots`
   - `GET /api/analytics/{id}/churn`
2. **Backend Execution:** [analytics.py](file:///c:/Users/mulla/Desktop/Projects/GitCompass/server/app/routers/analytics.py) handles requests, verifying user access to repo.
3. **Database RPC Call:** `analytics.py` calls Supabase RPC functions (`get_hotspots`, `get_churn_timeline`) defined in PostgreSQL migrations (`002_analytics_rpc.sql`).
4. **Data Presentation:** Data is rendered via custom interactive charts in `HotspotTreemap.jsx` and analytics cards.

---

### 4. Architecture Map Flow

```
[User] ──(Click Architecture Map)──▶ client/src/pages/ArchitectureMap.jsx
                                                │
                                                ▼ (GET /api/analytics/{id}/coupling)
                                      server/app/routers/analytics.py
                                                │
                                                ▼
                                      Supabase DB / RPC
                                                │
                                                ▼
                            React Flow Graph Transformation Engine
                                                │
                                                ▼
                             React Flow Canvas (<ReactFlow />)
```

**Call Sequence:**
1. `ArchitectureMap.jsx` fetches file co-change metrics from backend (`/api/analytics/{id}/coupling`).
2. Converts raw coupling records into React Flow `nodes` (representing files/modules) and `edges` (representing coupling strength).
3. Renders interactive graph canvas with drag, zoom, and focus filters.

---

### 5. AI Intelligence Flows (Phase 5)

```
[User] ──(Request Insight)──▶ client/src/components/AISummaryCard.jsx (or Timeline/Chat)
                                          │
                                          ▼ (POST /api/ai/...)
                                server/app/routers/ai.py
                                          │
                                          ▼ (Check Cache: ai_analysis_cache)
                                          │
                            ┌─────────────┴─────────────┐
                            │ (Cache Miss)              │ (Cache Hit)
                            ▼                           ▼
                server/app/services/ai_service.py     Return JSON
                            │
                            ▼ (Compile context)
                            │
                            ▼ (Google Gemini API)
                       google-genai
                            │
                            ▼ (Save to Cache)
                            │
                            ▼
                       Return JSON
```

**Call Sequence:**
1. **Frontend Request:** Components (e.g. `AISummaryCard`, `ArchitectureTimeline`, `QAChatAssistant`) send requests to `/api/ai/*` via `api.js`.
2. **Backend Router:** `ai.py` handles the request. It checks `ai_analysis_cache` using the latest commit SHA.
3. **Cache Logic:** If a valid cache exists, return it. Otherwise, invoke `ai_service.py`.
4. **AI Processing:** `ai_service.py` fetches necessary context from DB, checks the 500-commit limit for shift detection, and calls the Gemini API.
5. **Cache & Respond:** The response is cached in Supabase and returned to the frontend.

---

### 6. Redis & Docker Container Infrastructure Flow

```
[Docker Compose]
       │
       ├── gitcompass-server container (FastAPI :8000)
       │         │
       │         └── app/core/redis.py ──(redis.Redis(host="redis", port=6379))──▶ gitcompass-redis container (:6379)
       │                                                                                    │
       └── gitcompass-redis container (redis:7-alpine) ◀───────────────────────────────────┘
```

**Call Sequence:**
1. Docker Compose orchestrates containers over bridge network `gitcompass_default`.
2. `server/app/core/redis.py` initializes a `redis.Redis` instance targeting hostname `redis` and port `6379`.
3. Commands executed inside `gitcompass-server` container (e.g. `redis_client.ping()`) resolve `redis` to container `gitcompass-redis` via Docker DNS and return status.

---

## 🎯 Current Execution Path Under Modification

> **Active Task / Focus Area:** Explicit AI Model Selection & Component Layout Fixes
> **Modified Paths:**
> - `server/app/routers/ai.py` - AI endpoints accepting `AIModelChoice` in payload
> - `server/app/services/ai_service.py` - Explicit `selected_model` parameter injected into `build_provider_chain`
> - `client/src/lib/api.js` - Updated `getAISummary` and `getAIShifts` to accept payload
> - `client/src/components/AISummaryCard.jsx` - Added model dropdown and internal scroll constraints
> - `client/src/components/ArchitectureTimeline.jsx` - Added model dropdown
> - `client/src/components/AIDevelopmentStory.jsx` - Added model dropdown and internal scroll constraints

---

## 🔄 Execution Flow Update Checklist for Future Code Changes

When adding a feature or refactoring code:
- [ ] Update **System Architecture & Module Map** if new services/routers/components were added.
- [ ] Trace exact call paths from entrypoint (`App.jsx` or `main.py`) down to database or git execution.
- [ ] Update **Current Execution Path Under Modification** to point to the exact files and functions currently being changed.
