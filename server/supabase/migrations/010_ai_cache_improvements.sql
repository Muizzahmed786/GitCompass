-- ============================================================
-- GitCompass — Migration 010
-- AI Cache Improvements (Models and Story Support)
-- ============================================================

-- 1. Drop existing constraints
ALTER TABLE public.ai_analysis_cache 
    DROP CONSTRAINT IF EXISTS ai_analysis_cache_analysis_type_check;

ALTER TABLE public.ai_analysis_cache 
    DROP CONSTRAINT IF EXISTS ai_analysis_cache_repo_id_analysis_type_key;

-- 2. Add model column (defaulting to 'auto' for existing rows if any)
ALTER TABLE public.ai_analysis_cache 
    ADD COLUMN IF NOT EXISTS model TEXT NOT NULL DEFAULT 'auto';

-- 3. Add new check constraint allowing 'story'
ALTER TABLE public.ai_analysis_cache 
    ADD CONSTRAINT ai_analysis_cache_analysis_type_check 
    CHECK (analysis_type IN ('summary', 'shifts', 'story'));

-- 4. Add new unique constraint including model
ALTER TABLE public.ai_analysis_cache 
    ADD CONSTRAINT ai_analysis_cache_repo_id_analysis_type_model_key 
    UNIQUE(repo_id, analysis_type, model);
