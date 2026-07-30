# GIT Compass

> Transform a GitHub repository's raw Git history into analytical intelligence.

GIT Compass is a full-stack developer tool designed for developers onboarding to unfamiliar codebases and tech leads conducting architectural audits. Unlike tools that analyze what code currently *is*, this platform analyzes how it *evolved*.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React (Vite), Tailwind CSS v4, React Flow, Recharts |
| Backend | FastAPI (Python), Pydantic |
| Database & Auth | Supabase (PostgreSQL + Auth) |
| Git Layer | GitPython / subprocess |
| AI Layer | Gemini API (Phase 5) |

## Getting Started

### Prerequisites

- **Node.js** ≥ 18 (recommend 22 LTS)
- **Python** ≥ 3.11
- **Supabase project** with GitHub OAuth configured (see below)

### 1. Clone & Configure

```bash
# Server / Backend
cp server/.env.example server/.env
# Edit server/.env with your Supabase credentials:
#   SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_JWT_SECRET

# Client / Frontend
cp client/.env.example client/.env
# Edit client/.env with:
#   VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY
```

### 2. Set Up Supabase

1. Run all migrations in `server/supabase/migrations/` (001 through 004) in your Supabase Dashboard → SQL Editor.
2. Enable **GitHub** as an auth provider in Supabase Dashboard → Authentication → Providers.
3. Add `http://localhost:5173` to Supabase Dashboard → Authentication → URL Configuration → Redirect URLs.

### 3. Start the Backend (Server)

```bash
cd server

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# On Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt

# Run server with uvicorn
python -m uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### 4. Start the Frontend (Client)

```bash
cd client
npm install
npm run dev
```

Open `http://localhost:5173` — the Vite dev server proxies `/api` requests to FastAPI automatically.

## Architecture

```
┌──────────────┐    /api/*     ┌──────────────┐
│   React UI   │───(proxy)────▶│   FastAPI    │
│  Vite :5173  │               │    :8000     │
└──────────────┘               └──────┬───────┘
       │                              │
       │ anon key                     │ JWT-scoped / service key
       ▼                              ▼
┌──────────────────────────────────────────────┐
│              Supabase (PostgreSQL)            │
│       RLS policies enforce tenant isolation   │
└──────────────────────────────────────────────┘
```

## Project Structure

```
GitCompass/
├── server/
│   ├── app/
│   │   ├── main.py           # FastAPI entry point
│   │   ├── config.py         # Pydantic settings
│   │   ├── database.py       # Supabase client factories
│   │   ├── dependencies.py   # JWT auth + DB dependencies
│   │   ├── routers/          # API endpoints (analytics, repositories, health)
│   │   ├── schemas/          # Pydantic models
│   │   └── services/         # Mining engine, git extractor, cloner
│   └── supabase/
│       └── migrations/       # SQL migrations (001 to 004)
├── client/
│   ├── src/
│   │   ├── App.jsx           # Auth-gated root
│   │   ├── lib/              # Supabase client & API helpers
│   │   ├── pages/            # Login, Dashboard, RepositoryAnalytics, ArchitectureMap
│   │   └── components/       # Layout, StatusBadge, HotspotTreemap
│   └── vite.config.js        # Vite dev server + API proxy
└── README.md
```

## License

Private — all rights reserved.
