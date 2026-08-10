-- ============================================================
-- GitCompass — Unified Combined Schema
-- ============================================================
-- This file is a compilation of all previous migrations (001 to 005)
-- combined into a single, cohesive initialization script. 
-- It resolves all redundancies and ALTER TABLE statements by 
-- defining columns at table creation time.
-- ============================================================

-- ── Extensions ───────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ── 1. Profiles ──────────────────────────────────────────────
-- Mirrors auth.users with app-specific fields.

CREATE TABLE IF NOT EXISTS public.profiles (
    id           UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    avatar_url   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own profile"
    ON public.profiles FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = id);

CREATE POLICY "Users can update their own profile"
    ON public.profiles FOR UPDATE TO authenticated
    USING ((SELECT auth.uid()) = id)
    WITH CHECK ((SELECT auth.uid()) = id);

CREATE POLICY "Service can insert profiles"
    ON public.profiles FOR INSERT
    WITH CHECK (true);


-- ── 2. Repositories ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.repositories (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    github_url        TEXT NOT NULL,
    name              TEXT,
    default_branch    TEXT NOT NULL DEFAULT 'main',
    status            TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN ('pending', 'cloning', 'mining', 'ready', 'error')),
    error_message     TEXT,
    total_commits     INT NOT NULL DEFAULT 0,
    total_files       INT NOT NULL DEFAULT 0,
    mining_progress   INT DEFAULT 0,           -- From 005_mining_progress_schema
    latest_commit_sha TEXT,                    -- From 004_phase_4_5_schema
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.repositories ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own repositories"
    ON public.repositories FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can insert their own repositories"
    ON public.repositories FOR INSERT TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can update their own repositories"
    ON public.repositories FOR UPDATE TO authenticated
    USING ((SELECT auth.uid()) = user_id)
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can delete their own repositories"
    ON public.repositories FOR DELETE TO authenticated
    USING ((SELECT auth.uid()) = user_id);


-- ── 3. Commits ──────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.commits (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id      UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    sha          TEXT NOT NULL,
    author_name  TEXT,
    author_email TEXT,
    committed_at TIMESTAMPTZ,
    message      TEXT,
    insertions   INT NOT NULL DEFAULT 0,
    deletions    INT NOT NULL DEFAULT 0,
    commit_type  TEXT NOT NULL DEFAULT 'other',  -- From 004_phase_4_5_schema
    UNIQUE(repo_id, sha)
);

ALTER TABLE public.commits ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own commits"
    ON public.commits FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can insert their own commits"
    ON public.commits FOR INSERT TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can delete their own commits"
    ON public.commits FOR DELETE TO authenticated
    USING ((SELECT auth.uid()) = user_id);


-- ── 4. File Diffs ───────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.file_diffs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_id   UUID NOT NULL REFERENCES public.commits(id) ON DELETE CASCADE,
    repo_id     UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_path   TEXT NOT NULL,
    old_path    TEXT,
    is_rename   BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted  BOOLEAN NOT NULL DEFAULT FALSE, -- From 003_add_is_deleted
    insertions  INT NOT NULL DEFAULT 0,
    deletions   INT NOT NULL DEFAULT 0
);

ALTER TABLE public.file_diffs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view their own file_diffs"
    ON public.file_diffs FOR SELECT TO authenticated
    USING ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can insert their own file_diffs"
    ON public.file_diffs FOR INSERT TO authenticated
    WITH CHECK ((SELECT auth.uid()) = user_id);

CREATE POLICY "Users can delete their own file_diffs"
    ON public.file_diffs FOR DELETE TO authenticated
    USING ((SELECT auth.uid()) = user_id);


-- ── 5. AI Analysis Cache ─────────────────────────────────────
-- From 005_ai_cache.sql

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

CREATE POLICY "Service can insert/update AI cache"
    ON public.ai_analysis_cache FOR ALL
    USING (true)
    WITH CHECK (true);


-- ── 6. Indexes ───────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_repositories_user_id  ON public.repositories(user_id);
CREATE INDEX IF NOT EXISTS idx_commits_user_id       ON public.commits(user_id);
CREATE INDEX IF NOT EXISTS idx_file_diffs_user_id    ON public.file_diffs(user_id);

CREATE INDEX IF NOT EXISTS idx_commits_repo_date     ON public.commits(repo_id, committed_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_diffs_repo_path  ON public.file_diffs(repo_id, file_path);
CREATE INDEX IF NOT EXISTS idx_commits_sha           ON public.commits(repo_id, sha);
CREATE INDEX IF NOT EXISTS idx_commits_commit_type   ON public.commits(repo_id, commit_type); -- From 004


-- ── 7. Triggers & Functions ──────────────────────────────────

-- Auto-Profile Trigger
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, display_name, avatar_url)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data ->> 'full_name',
        NEW.raw_user_meta_data ->> 'avatar_url'
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();


-- Updated-at Trigger
CREATE OR REPLACE FUNCTION public.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_repositories_updated_at ON public.repositories;
CREATE TRIGGER set_repositories_updated_at
    BEFORE UPDATE ON public.repositories
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();

DROP TRIGGER IF EXISTS set_ai_analysis_cache_updated_at ON public.ai_analysis_cache;
CREATE TRIGGER set_ai_analysis_cache_updated_at
    BEFORE UPDATE ON public.ai_analysis_cache
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at();


-- ── 8. RPC Functions ──────────────────────────────────────────
-- From 002_analytics_rpc.sql

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
        jsonb_agg(DISTINCT c.author_name) AS authors
    FROM public.file_diffs fd
    JOIN public.commits c ON c.id = fd.commit_id
    WHERE fd.repo_id = p_repo_id
    GROUP BY fd.file_path
    ORDER BY commits_count DESC;
$$;
