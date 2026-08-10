-- ============================================================
-- GitCompass — Migration 005
-- AI Cache Table
-- ============================================================

CREATE TABLE IF NOT EXISTS public.ai_analysis_cache (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id       UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    analysis_type TEXT NOT NULL CHECK (analysis_type IN ('summary', 'shifts')),
    latest_sha    TEXT NOT NULL,
    content       JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(repo_id, analysis_type)
);

ALTER TABLE public.ai_analysis_cache ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view AI cache for their repos"
    ON public.ai_analysis_cache FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.repositories
            WHERE id = repo_id AND user_id = (SELECT auth.uid())
        )
    );

-- Only service role (backend) should insert/update this cache
CREATE POLICY "Service can insert/update AI cache"
    ON public.ai_analysis_cache FOR ALL
    USING (true)
    WITH CHECK (true);

-- Updated_at trigger
CREATE TRIGGER set_ai_analysis_cache_updated_at
    BEFORE UPDATE ON public.ai_analysis_cache
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();
