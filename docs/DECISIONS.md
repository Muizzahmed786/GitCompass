# Architectural Decisions

## 2026-09-03: Modular Monolith Refactoring
**Decision:** Refactored the FastAPI monolith to enforce strict separation of concerns, moving business logic from routers into a dedicated service layer.

**Why:** The router files (`analytics.py`, `ai.py`) were growing too large and accumulating business logic (e.g., complex pandas-style aggregations for hotspots, AI provider fallback handling). This violated the Single Responsibility Principle and made testing difficult.

**Trade-offs:** 
- Introduces more files and slight indirection (e.g., `routers/analytics.py` -> `services/analytics_service.py`).
- Kept the monolith structure rather than splitting into microservices, prioritizing developer velocity and operational simplicity while ensuring the codebase is modular enough to split later if necessary.

**Specific Outcomes:**
- **Thin Routers:** Routers only handle HTTP request parsing, validation, and response serialization.
- **Dedicated Services:** Extracted `analytics_service.py`, `ai_cache.py`, `chat_retrieval.py`, `ai_providers.py`, and `ai_prompts.py`.
- **Shared Schemas:** Pydantic models extracted from routers to `schemas/analytics.py` and `schemas/ai.py`.

## 2026-09-04: Architecture Visualization Engine
**Decision:** Adopted `@xyflow/react` (React Flow) and `dagre` for the Stage 9 Architecture Visualization layer, backed by a thin, UI-agnostic FastAPI endpoint (`/knowledge-graph`).

**Why:** React Flow provides an out-of-the-box, highly interactive node/edge canvas (zoom, pan, drag) that would be excessively complex to build from scratch with D3.js. `dagre` was chosen for deterministic hierarchical layout to avoid chaotic, overlapping force-directed graphs in large repositories.

**Trade-offs:** 
- **Large Graph Performance:** React Flow can lag with thousands of nodes. To mitigate this, the backend groups source files into module-level nodes (by top-level directory) and caps the graph size. Deep file-level analytics are loaded dynamically on demand via `NodeInspector` rather than rendered in the main graph.
- **Dependency Weight:** Adds `@xyflow/react` to the frontend bundle, but the rich interaction (essential for architecture exploration) justifies the cost.

**Specific Outcomes:**
- **UI-Agnostic Backend:** `server/app/schemas/analytics.py` defines pure `GraphNode` and `GraphEdge` models. React Flow specific mapping happens entirely in `ArchitectureGraph.jsx`.
- **Dynamic Drill-down:** `NodeInspector.jsx` reuses the existing `/api/analytics/{repo_id}/hotspots` endpoint to derive intelligence, preventing API duplication.

**Post-Implementation Review (Stage 9 Architecture Validation):**
- **Knowledge Model Boundary:** `knowledge_graph.py` queries `repository_dependencies` and `repository_source_files` directly. This is because these PostgreSQL tables *are* the native structural representations of the Repository Knowledge Model. We deliberately avoided creating an intermediate Python abstraction layer to keep the transformation thin and prevent dual-schema drift.
- **Module Detection:** In the MVP, a "module" is structurally defined as the top-level directory of a source file. This aligns with standard monorepo/microservice boundaries without introducing a new, conflicting detection heuristic.
- **NodeInspector Semantic Mapping:** NodeInspector filters the `/hotspots` dataset by module prefix to calculate file counts and commit velocity. Since hotspots only tracks *modified* files, the inspector intentionally reflects active evolutionary footprint rather than static file counts, aligning perfectly with GitCompass' focus on temporal evolution.
