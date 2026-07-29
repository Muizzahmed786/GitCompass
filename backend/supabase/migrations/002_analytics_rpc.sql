-- ============================================================
-- GitCompass — Analytics RPC Migration
-- ============================================================
-- Creates the get_repo_hotspots function for Phase 3 analytics
-- ============================================================

CREATE OR REPLACE FUNCTION public.get_repo_hotspots(p_repo_id UUID)
RETURNS TABLE (
    file_path TEXT,
    commits_count BIGINT,
    total_insertions BIGINT,
    total_deletions BIGINT,
    authors JSONB
)
LANGUAGE sql
SECURITY INVOKER
AS $$
    SELECT 
        fd.file_path,
        COUNT(DISTINCT fd.commit_id) AS commits_count,
        SUM(fd.insertions) AS total_insertions,
        SUM(fd.deletions) AS total_deletions,
        -- Aggregate unique authors using jsonb_agg and DISTINCT
        jsonb_agg(DISTINCT c.author_name) AS authors
    FROM public.file_diffs fd
    JOIN public.commits c ON c.id = fd.commit_id
    WHERE fd.repo_id = p_repo_id
    GROUP BY fd.file_path
    ORDER BY commits_count DESC;
$$;
