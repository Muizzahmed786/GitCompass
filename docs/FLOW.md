# Execution Flow

## Analytics Flow
1. **Client** requests `/api/analytics/{repo_id}/...` via HTTP.
2. **`routers/analytics.py`**:
   - Parses request parameters and query strings.
   - Validates repository ownership.
   - Delegates to `services/analytics_service.py` via `calculate_hotspots`, `calculate_temporal_coupling`, `calculate_bus_factor`, or `calculate_summary`.
3. **`services/analytics_service.py`**:
   - Executes Supabase PostgREST queries via the `db` client to fetch `file_diffs` and `commits`.
   - Aggregates and transforms the data in Python (e.g. coupling matrices, bus factor calculation).
4. **Response**: Data is serialized using Pydantic models from `schemas/analytics.py` and returned to the client.

## AI Generation Flow (Summary, Shifts, Story)
1. **Client** requests an AI generation endpoint via `routers/ai.py`.
2. **Cache Check (`services/ai_cache.py`)**:
   - Checks if a valid cached response exists for the specific repository, model, and commit SHA.
   - Returns immediately if a valid cache hit occurs.
3. **Evidence Assembly (`services/evidence_assembler.py`)**:
   - Fetches chronological, structured repository history from the database.
4. **AI Processing (`services/ai_service.py`)**:
   - Selects the appropriate prompt from `services/ai_prompts.py`.
   - Delegates to `generate_ai_response` in `services/ai_providers.py`.
5. **Provider Execution (`services/ai_providers.py`)**:
   - Selects the target provider (Gemini or Groq).
   - Attempts generation. On infrastructure errors (Rate Limit, Unavailable), falls back to the next provider in the chain.
6. **Post-Processing**:
   - JSON output is validated and parsed using `extract_json` from `services/ai_prompts.py`.
   - Result is saved to the database cache via `services/ai_cache.py`.
7. **Response**: Returned to the client.

## AI Chat Flow
1. **Client** sends a chat payload (history + context) to `/api/ai/chat/{repo_id}` in `routers/ai.py`.
2. **Evidence Assembly**: General repository evidence is assembled.
3. **Context Retrieval (`services/chat_retrieval.py`)**:
   - Extracts explicit file selection from UI payload.
   - Scans the latest user message for file paths using regex.
   - If a specific file is identified, retrieves its isolated context (slice) from the DB.
4. **QA Generation (`services/ai_service.py`)**:
   - Invokes `answer_qa` with both general evidence and specific slice.
   - Uses the provider chain in `services/ai_providers.py`.
5. **Response**: Citations are validated against supplied paths and the answer is returned.

## Current Execution Path Under Modification
None currently. Refactoring complete.
