-- ============================================================
-- GitCompass — Initial Schema Migration
-- ============================================================
-- Run this in your Supabase Dashboard → SQL Editor, or via
-- the Supabase CLI: supabase db push
--
-- Tables: profiles, repositories, commits, file_diffs
-- All tables have Row-Level Security enabled.
-- ============================================================


-- ── Extensions ───────────────────────────────────────────────

-- gen_random_uuid() is available by default in Supabase, but
-- enable explicitly for safety.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- ── 1. Profiles ──────────────────────────────────────────────
-- Mirrors auth.users with app-specific fields.
-- Populated automatically by a trigger on user signup.

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

-- Allow the trigger (SECURITY DEFINER) to insert profiles
CREATE POLICY "Service can insert profiles"
    ON public.profiles FOR INSERT
    WITH CHECK (true);


-- ── 2. Repositories ─────────────────────────────────────────

CREATE TABLE IF NOT EXISTS public.repositories (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    github_url     TEXT NOT NULL,
    name           TEXT,
    default_branch TEXT NOT NULL DEFAULT 'main',
    status         TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'cloning', 'mining', 'ready', 'error')),
    error_message  TEXT,
    total_commits  INT NOT NULL DEFAULT 0,
    total_files    INT NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
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
-- user_id is denormalized from repositories for fast RLS checks.

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
-- user_id is denormalized from repositories for fast RLS checks.
-- old_path tracks file renames (Phase 2, -M flag).

CREATE TABLE IF NOT EXISTS public.file_diffs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    commit_id   UUID NOT NULL REFERENCES public.commits(id) ON DELETE CASCADE,
    repo_id     UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    file_path   TEXT NOT NULL,
    old_path    TEXT,
    is_rename   BOOLEAN NOT NULL DEFAULT FALSE,
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


-- ── Indexes ─────────────────────────────────────────────────

-- RLS performance (direct user_id lookups)
CREATE INDEX IF NOT EXISTS idx_repositories_user_id  ON public.repositories(user_id);
CREATE INDEX IF NOT EXISTS idx_commits_user_id       ON public.commits(user_id);
CREATE INDEX IF NOT EXISTS idx_file_diffs_user_id    ON public.file_diffs(user_id);

-- Analytics queries (Phase 3+)
CREATE INDEX IF NOT EXISTS idx_commits_repo_date     ON public.commits(repo_id, committed_at DESC);
CREATE INDEX IF NOT EXISTS idx_file_diffs_repo_path  ON public.file_diffs(repo_id, file_path);
CREATE INDEX IF NOT EXISTS idx_commits_sha           ON public.commits(repo_id, sha);


-- ── Auto-Profile Trigger ────────────────────────────────────
-- When a new user signs up via Supabase Auth, automatically
-- create a profiles row with their GitHub display name + avatar.

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

-- Drop and recreate to make migration idempotent
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();


-- ── Updated-at Trigger ──────────────────────────────────────
-- Automatically set updated_at on repositories when modified.

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
