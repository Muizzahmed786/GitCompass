import { useState, useEffect } from "react";
import { supabase } from "./lib/supabase";
import Layout from "./components/Layout";
import LandingPage from "./pages/LandingPage";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import RepositoryAnalytics from "./pages/RepositoryAnalytics";
import ArchitectureMap from "./pages/ArchitectureMap";
import RepositoryEvolution from "./pages/RepositoryEvolution";
import RepositoryHotspots from "./pages/RepositoryHotspots";
import RepositoryContributors from "./pages/RepositoryContributors";
import RepositoryAIInsights from "./pages/RepositoryAIInsights";
import { ThemeProvider } from "./lib/ThemeContext";

import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

// Protected Route Wrapper
const ProtectedRoute = ({ session, children }) => {
  if (!session) return <Navigate to="/login" replace />;
  return <Layout user={session.user}>{children}</Layout>;
};

export default function App() {
  const [session, setSession] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setLoading(false);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-[var(--color-surface)] flex items-center justify-center">
        <div className="text-center">
          <div className="text-technical text-2xl font-bold animate-pulse">LOADING...</div>
        </div>
      </div>
    );
  }

  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Routes */}
          <Route path="/" element={session ? <Navigate to="/dashboard" replace /> : <LandingPage />} />
          <Route path="/login" element={session ? <Navigate to="/dashboard" replace /> : <Login />} />
          <Route path="/register" element={session ? <Navigate to="/dashboard" replace /> : <Register />} />

          {/* Protected Routes */}
          <Route path="/dashboard" element={<ProtectedRoute session={session}><Dashboard user={session?.user} /></ProtectedRoute>} />
          <Route path="/repository/:id" element={<ProtectedRoute session={session}><RepositoryAnalytics user={session?.user} /></ProtectedRoute>} />
          <Route path="/repository/:id/evolution" element={<ProtectedRoute session={session}><RepositoryEvolution user={session?.user} /></ProtectedRoute>} />
          <Route path="/repository/:id/architecture" element={<ProtectedRoute session={session}><ArchitectureMap user={session?.user} /></ProtectedRoute>} />
          <Route path="/repository/:id/hotspots" element={<ProtectedRoute session={session}><RepositoryHotspots user={session?.user} /></ProtectedRoute>} />
          <Route path="/repository/:id/contributors" element={<ProtectedRoute session={session}><RepositoryContributors user={session?.user} /></ProtectedRoute>} />
          <Route path="/repository/:id/ai" element={<ProtectedRoute session={session}><RepositoryAIInsights user={session?.user} /></ProtectedRoute>} />
          
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  );
}
