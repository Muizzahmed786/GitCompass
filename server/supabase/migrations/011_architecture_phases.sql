-- Migration 011: Architecture Phases
--
-- Records deterministic architectural evolution phases grouped by
-- the Architecture Evolution Engine (Stage 6).

CREATE TABLE public.architecture_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID NOT NULL REFERENCES public.repositories(id) ON DELETE CASCADE,
    phase_index INTEGER NOT NULL,
    start_date TIMESTAMPTZ NOT NULL,
    end_date TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL,
    dominant_event_type TEXT,
    event_count INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT timezone('utc'::text, now())
);

-- Ensure a repository doesn't have duplicate phase indices
CREATE UNIQUE INDEX idx_architecture_phases_repo_index 
    ON public.architecture_phases(repo_id, phase_index);

-- The evidence mapping table
CREATE TABLE public.architecture_phase_events (
    phase_id UUID NOT NULL REFERENCES public.architecture_phases(id) ON DELETE CASCADE,
    event_id UUID NOT NULL REFERENCES public.repository_events(id) ON DELETE CASCADE,
    PRIMARY KEY (phase_id, event_id)
);

-- Row Level Security
ALTER TABLE public.architecture_phases ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their architecture phases" ON public.architecture_phases
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.repositories 
            WHERE id = architecture_phases.repo_id 
            AND user_id = auth.uid()
        )
    );

ALTER TABLE public.architecture_phase_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their architecture phase events" ON public.architecture_phase_events
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.architecture_phases p
            JOIN public.repositories r ON r.id = p.repo_id
            WHERE p.id = architecture_phase_events.phase_id 
            AND r.user_id = auth.uid()
        )
    );
