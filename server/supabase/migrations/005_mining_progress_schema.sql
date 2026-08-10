-- ============================================================
-- GitCompass — Migration 005: Mining Progress Tracking
-- ============================================================
-- 1. Add mining_progress to public.repositories
-- ============================================================

ALTER TABLE public.repositories
ADD COLUMN IF NOT EXISTS mining_progress INT DEFAULT 0;
