# File Contracts

## `routers/analytics.py`
**Interface:** HTTP Endpoints
- **Inputs:** HTTP GET requests containing `repo_id`, `start_date`, `end_date`, `commit_type`, `threshold`, `max_commit_files`.
- **Outputs:** JSON responses serialized via `app.schemas.analytics`.

## `services/analytics_service.py`
**Interface:** Python Functions
- **Inputs:** Supabase `db` client, `repo_id`, and filtering parameters.
- **Outputs:** Python dictionaries representing aggregated analytics data (Hotspots, Coupling, Bus Factor, Summary) ready for Pydantic serialization.

## `routers/ai.py`
**Interface:** HTTP Endpoints
- **Inputs:** HTTP POST requests containing `repo_id`, and optional `AIRequest` payload (`model`, `force_refresh`).
- **Outputs:** JSON responses serialized via `app.schemas.ai` containing AI-generated text.

## `services/ai_service.py`
**Interface:** Domain Service
- **Inputs:** `repo_name`, `evidence` dictionary, and `selected_model`.
- **Outputs:** Python dictionaries containing the structural outputs (Summary, Shifts, Story) parsed from the AI provider's JSON response.

## `services/ai_providers.py`
**Interface:** Provider Chain
- **Inputs:** `task_type` (for model routing), `system_prompt`, `user_prompt`, `temperature`, `selected_model`.
- **Outputs:** Dictionary containing `{"text": "<generated text>", "provider_name": "<provider used>"}`.
- **Side Effects:** Automatically retries across different configured providers (Gemini, Groq) on network or quota failures. Raises `AllProvidersFailedError` if exhaustion occurs.

## `services/ai_cache.py`
**Interface:** Cache Management
- **Inputs:** Supabase `db` client, `repo_id`, `analysis_type`, `selected_model`, `latest_sha`.
- **Outputs:** For checking: `(hit_boolean, cached_payload_dict)`. For saving: None (Side effect: database mutation).

## `services/chat_retrieval.py`
**Interface:** Context Resolution
- **Inputs:** Supabase `db` client, `repo_id`, `evidence`, `history` (list of messages), `page_context`.
- **Outputs:** `(specific_slice_dict, supplied_paths_set)` for targeted contextual Q&A.

## `services/miner.py`
**Interface:** Background Tasks
- **Inputs:** `repo_id`, GitHub URL, `db` client, etc.
- **Outputs:** Side effects only. Clones repositories, processes commits/diffs, updates database tables, and executes background deletions.
