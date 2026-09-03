import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import AISummaryCard from "../components/AISummaryCard";

export default function RepositoryAIInsights() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const repoData = await api.get(`/api/repositories/${id}`);
      setRepo(repoData);
    } catch (err) {
      setError(err.message || "Failed to load repository");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return <div className="card p-12 text-center text-text-secondary animate-pulse-soft">Loading AI Insights...</div>;
  }

  if (error) {
    return (
      <div className="card p-12 text-center text-error bg-error-light">
        <p className="font-medium">Error loading repository</p>
        <p className="text-sm mt-1">{error}</p>
        <Link to={`/repository/${id}`} className="text-primary-600 text-sm mt-4 inline-block underline">
          ← Back to Overview
        </Link>
      </div>
    );
  }

  if (!repo) return null;

  return (
    <div className="animate-fade-in pb-12">
      <div className="mb-8">
        <Link to={`/repository/${id}`} className="inline-flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-primary transition-colors mb-4">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Overview
        </Link>
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-text-primary tracking-tight">
            {repo.name || repo.github_url} — AI Insights
          </h1>
          <span className="badge badge-special text-[10px]">Beta</span>
        </div>
        <p className="mt-1 text-sm text-text-secondary">
          Deep architectural reasoning and summaries
        </p>
        
        <div className="mt-6 p-4 bg-[var(--color-surface-raised)] border-2 border-[var(--color-border)] shadow-[4px_4px_0px_var(--color-border)] flex items-start gap-4 max-w-3xl">
          <div className="text-[var(--color-special)] mt-1">
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
               <path strokeLinecap="square" strokeLinejoin="miter" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="font-black uppercase text-sm tracking-wider mb-1">Feature in Development</h3>
            <p className="text-sm text-[var(--color-text-secondary)] leading-relaxed">
              This feature is still in active development. AI-generated results may not be perfectly consistent yet, and many more features are yet to come!
            </p>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1">
        <AISummaryCard repoId={id} />
      </div>
    </div>
  );
}
