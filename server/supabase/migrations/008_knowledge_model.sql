-- Migration 008: Repository Knowledge Model

-- 1. repository_knowledge table
CREATE TABLE public.repository_knowledge (
    repo_id UUID PRIMARY KEY REFERENCES public.repositories(id) ON DELETE CASCADE,
    latest_analyzed_sha TEXT,
    structure JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now())
);

ALTER TABLE public.repository_knowledge ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their repository knowledge" ON public.repository_knowledge
    FOR SELECT USING (EXISTS (SELECT 1 FROM public.repositories WHERE id = repository_knowledge.repo_id AND user_id = auth.uid()));

-- 2. repository_dependencies table
CREATE TABLE public.repository_dependencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID REFERENCES public.repositories(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    version TEXT,
    ecosystem TEXT,
    category TEXT,
    evidence_path TEXT
);

CREATE INDEX idx_repository_dependencies_repo_name ON public.repository_dependencies(repo_id, name);

ALTER TABLE public.repository_dependencies ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their repository dependencies" ON public.repository_dependencies
    FOR SELECT USING (EXISTS (SELECT 1 FROM public.repositories WHERE id = repository_dependencies.repo_id AND user_id = auth.uid()));

-- 3. repository_source_files table
CREATE TABLE public.repository_source_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id UUID REFERENCES public.repositories(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    language TEXT,
    imports JSONB DEFAULT '[]'::jsonb,
    classes JSONB DEFAULT '[]'::jsonb,
    functions JSONB DEFAULT '[]'::jsonb
);

CREATE INDEX idx_repository_source_files_repo_path ON public.repository_source_files(repo_id, file_path);
-- Optional GIN indexes if we perform heavy cross-repo jsonb queries, but typically queried by repo_id first.
CREATE INDEX idx_repository_source_files_imports ON public.repository_source_files USING GIN (imports);
CREATE INDEX idx_repository_source_files_classes ON public.repository_source_files USING GIN (classes);
CREATE INDEX idx_repository_source_files_functions ON public.repository_source_files USING GIN (functions);

ALTER TABLE public.repository_source_files ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can access their repository source files" ON public.repository_source_files
    FOR SELECT USING (EXISTS (SELECT 1 FROM public.repositories WHERE id = repository_source_files.repo_id AND user_id = auth.uid()));

-- 4. Atomic Replace RPC Function
CREATE OR REPLACE FUNCTION replace_knowledge_model(
    p_repo_id UUID,
    p_latest_sha TEXT,
    p_structure JSONB,
    p_dependencies JSONB,
    p_source_files JSONB
) RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Upsert Knowledge
    INSERT INTO public.repository_knowledge (repo_id, latest_analyzed_sha, structure)
    VALUES (p_repo_id, p_latest_sha, p_structure)
    ON CONFLICT (repo_id) DO UPDATE SET 
        latest_analyzed_sha = EXCLUDED.latest_analyzed_sha,
        structure = EXCLUDED.structure,
        updated_at = timezone('utc'::text, now());

    -- Delete existing dependencies and source files for fresh replacement
    DELETE FROM public.repository_dependencies WHERE repo_id = p_repo_id;
    DELETE FROM public.repository_source_files WHERE repo_id = p_repo_id;

    -- Insert new dependencies
    IF jsonb_typeof(p_dependencies) = 'array' THEN
        INSERT INTO public.repository_dependencies (repo_id, name, version, ecosystem, category, evidence_path)
        SELECT 
            p_repo_id,
            d->>'name',
            d->>'version',
            d->>'ecosystem',
            d->>'category',
            d->>'evidence_path'
        FROM jsonb_array_elements(p_dependencies) AS d;
    END IF;

    -- Insert new source files
    IF jsonb_typeof(p_source_files) = 'array' THEN
        INSERT INTO public.repository_source_files (repo_id, file_path, language, imports, classes, functions)
        SELECT 
            p_repo_id,
            f->>'file_path',
            f->>'language',
            COALESCE(f->'imports', '[]'::jsonb),
            COALESCE(f->'classes', '[]'::jsonb),
            COALESCE(f->'functions', '[]'::jsonb)
        FROM jsonb_array_elements(p_source_files) AS f;
    END IF;
END;
$$;
