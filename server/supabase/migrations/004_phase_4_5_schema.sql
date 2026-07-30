-- ============================================================
-- GitCompass — Migration 004: Phase 4.5 Analytics Schema Updates
-- ============================================================
-- 1. Add commit_type to public.commits for Conventional Commit classification
-- 2. Add latest_commit_sha to public.repositories for Incremental Sync
-- ============================================================

ALTER TABLE public.commits
ADD COLUMN IF NOT EXISTS commit_type TEXT NOT NULL DEFAULT 'other';

ALTER TABLE public.repositories
ADD COLUMN IF NOT EXISTS latest_commit_sha TEXT;

-- Index for fast conventional commit filtering in analytics queries
CREATE INDEX IF NOT EXISTS idx_commits_commit_type ON public.commits(repo_id, commit_type);
