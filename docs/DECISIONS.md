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
