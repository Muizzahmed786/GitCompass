import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";

export default function RepositoryContributors() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [busFactor, setBusFactor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const repoData = await api.get(`/api/repositories/${id}`);
      setRepo(repoData);

      const busFactorData = await api.get(`/api/analytics/${id}/bus-factor`).catch(() => null);
      setBusFactor(busFactorData);
    } catch (err) {
      setError(err.message || "Failed to load contributors analytics");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return <div className="card p-12 text-center text-text-secondary animate-pulse-soft">Loading contributors...</div>;
  }

  if (error) {
    return (
      <div className="card p-12 text-center text-error bg-error-light">
        <p className="font-medium">Error loading contributors</p>
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
        <Link
          to={`/repository/${id}`}
          className="inline-flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-primary transition-colors mb-4"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Overview
        </Link>
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">
          {repo.name || repo.github_url} — Contributors
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Bus Factor, Ownership & Module Expertise
        </p>
      </div>

      {busFactor && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="card-flat p-6">
            <h2 className="text-sm font-semibold text-text-primary mb-6 flex items-center gap-2">
              <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Top Contributors
              <span className={`ml-2 px-2.5 py-1 rounded-full text-xs font-bold ${busFactor.repo_bus_factor <= 2 ? "bg-rose-100 text-rose-700" : busFactor.repo_bus_factor <= 4 ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"}`}>
                Bus Factor: {busFactor.repo_bus_factor}
              </span>
            </h2>
            <div className="space-y-6">
              {Object.entries(busFactor.top_contributors || {}).map(([author, count]) => {
                const total = Object.values(busFactor.top_contributors).reduce((s, v) => s + v, 0) || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={author} className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-sm font-bold text-primary-700 shrink-0">
                      {author.slice(0, 1).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between text-sm mb-2">
                        <span className="text-text-primary font-medium truncate">{author}</span>
                        <div className="flex items-center gap-3">
                           <span className="text-text-secondary text-xs">{count} commits</span>
                           <span className="text-text-tertiary shrink-0 font-mono text-sm">{pct}%</span>
                        </div>
                      </div>
                      <div className="h-2.5 bg-surface-hover rounded-full overflow-hidden">
                        <div className="h-full bg-primary-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
