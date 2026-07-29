/**
 * App — Root component with auth-gated routing.
 *
 * Subscribes to supabase.auth.onAuthStateChange and renders:
 * - <Login /> for unauthenticated users
 * - <Layout><Dashboard /></Layout> for authenticated users
 *
 * Session state is managed via Supabase's built-in listener,
 * so OAuth redirects and token refreshes are handled automatically.
 */

import { useState, useEffect } from "react";
import { supabase } from "./lib/supabase";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Dashboard from "./pages/Dashboard";
import RepositoryAnalytics from "./pages/RepositoryAnalytics";

import { BrowserRouter, Routes, Route } from "react-router-dom";

export default function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Get the initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    // Listen for auth state changes (login, logout, token refresh)
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  // Show nothing while we check for an existing session
  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="text-center animate-fade-in">
          <div className="inline-flex items-center justify-center w-10 h-10 bg-primary-100 rounded-xl mb-3">
            <svg
              className="w-5 h-5 text-primary-600 animate-pulse-soft"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7"
              />
            </svg>
          </div>
          <p className="text-sm text-text-secondary">Loading…</p>
        </div>
      </div>
    );
  }

  // Not authenticated → show login
  if (!session) {
    return <Login />;
  }

  // Authenticated → show dashboard with routing
  return (
    <BrowserRouter>
      <Layout user={session.user}>
        <Routes>
          <Route path="/" element={<Dashboard user={session.user} />} />
          {/* We will create RepositoryAnalytics component shortly */}
          <Route path="/repository/:id" element={<RepositoryAnalytics user={session.user} />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
