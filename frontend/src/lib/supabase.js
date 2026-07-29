/**
 * Supabase client singleton.
 *
 * Uses the ANON key — the service role key never touches the browser.
 * All database queries from the frontend are subject to PostgreSQL
 * Row-Level Security policies.
 */

import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    "Missing Supabase environment variables. " +
      "Copy .env.example to .env and fill in your project credentials."
  );
}

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
