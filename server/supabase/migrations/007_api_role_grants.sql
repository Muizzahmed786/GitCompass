-- ============================================================
-- GitCompass — API Role Grants
-- ============================================================
-- Explicitly grant privileges to the authenticated and service_role 
-- so that the Supabase REST/GraphQL APIs can access the tables.
-- ============================================================

-- Grant usage on the public schema
GRANT USAGE ON SCHEMA public TO authenticated, service_role;

-- Grant privileges on all existing tables
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO authenticated, service_role;

-- Ensure privileges are granted for any tables created in the future
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO authenticated, service_role;
