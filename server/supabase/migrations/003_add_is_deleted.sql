-- ============================================================
-- Migration 003: Add is_deleted to file_diffs
-- ============================================================

ALTER TABLE public.file_diffs
ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE;
