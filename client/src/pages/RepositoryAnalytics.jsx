import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";

export default function RepositoryAnalytics() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [summary, setSummary] = useState(null);
  const [busFactor, setBusFactor] = useState(null);
  const [aiPreview, setAiPreview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const repoData = await api.get(`/api/repositories/${id}`);
      setRepo(repoData);

      // Sequential fetch to prevent backend connection pool exhaustion
      const summaryData = await api.get(`/api/analytics/${id}/summary`).catch(e => { console.error('Summary error', e); return null; });
      const busFactorData = await api.get(`/api/analytics/${id}/bus-factor`).catch(e => { console.error('Bus factor error', e); return null; });
      const hotspotsData = await api.get(`/api/analytics/${id}/hotspots`).catch(e => { console.error('Hotspots error', e); return null; });
      const aiRes = await api.getAISummary(id, { force_refresh: false }).catch(e => { console.error('AI preview error', e); return null; });

      setHotspots(hotspotsData || []);
      setSummary(summaryData);
      setBusFactor(busFactorData);
      
      if (aiRes && aiRes.is_cached && aiRes.summary) {
        setAiPreview(aiRes.summary.repository_summary || "AI Summary generated.");
      }
    } catch (err) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { loadData(); }, [loadData]);

  if (loading) {
    return (
      <div className="card-flat p-12 text-center text-text-secondary animate-pulse-soft">
        Loading Overview…
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-flat p-12 text-center text-error bg-error-light">
        <p className="font-medium">Error loading Overview</p>
        <p className="text-sm mt-1">{error}</p>
        <Link to="/" className="text-primary-600 text-sm mt-4 inline-block underline">
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  if (!repo) return null;

  // Derive simple metrics
  const activeHotspots = (hotspots || []).filter(h => !h.is_deleted);
  const topActive = activeHotspots.slice(0, 5); // Take top 5 for preview
  const topContributors = Object.entries(busFactor?.top_contributors || {}).slice(0, 3);
  const isHealthy = busFactor && busFactor.repo_bus_factor > 4;
  
  // Truncate AI Preview to roughly the first sentence or 120 chars
  const truncatedAI = aiPreview ? (aiPreview.length > 150 ? aiPreview.slice(0, 150).trim() + "..." : aiPreview) : null;

  return (
    <div className="animate-fade-in pb-12 max-w-7xl mx-auto">
      {/* ── Repository Header ────────────────────────── */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <Link
            to="/"
            className="inline-flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-primary transition-colors mb-4"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Dashboard
          </Link>
          <h1 className="text-3xl font-black text-text-primary tracking-tight">
            {repo.name || repo.github_url}
          </h1>
          <p className="mt-1 text-sm text-text-secondary uppercase tracking-wider font-semibold">
            Repository Intelligence Overview
          </p>
        </div>
      </div>

      {/* ── Repository Snapshot ────────────────────────── */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
          <div className="card-flat p-5 border-l-4 border-l-primary-500">
            <p className="text-[10px] text-text-tertiary font-black uppercase tracking-widest">Commits</p>
            <p className="text-3xl font-black text-text-primary mt-1">{(summary.total_commits || 0).toLocaleString()}</p>
          </div>
          <div className="card-flat p-5 border-l-4 border-l-emerald-500">
            <p className="text-[10px] text-text-tertiary font-black uppercase tracking-widest">Contributors</p>
            <p className="text-3xl font-black text-text-primary mt-1">{Object.keys(busFactor?.top_contributors || {}).length}</p>
          </div>
          <div className="card-flat p-5 border-l-4 border-l-info">
            <p className="text-[10px] text-text-tertiary font-black uppercase tracking-widest">Total Files</p>
            <p className="text-3xl font-black text-text-primary mt-1">{summary.total_files.toLocaleString()}</p>
          </div>
          <div className="card-flat p-5 border-l-4 border-l-warning">
            <p className="text-[10px] text-text-tertiary font-black uppercase tracking-widest">Activity Level</p>
            <p className="text-xl font-black text-text-primary mt-2">
              {summary.total_commits > 1000 ? "HIGH" : summary.total_commits > 100 ? "MEDIUM" : "LOW"}
            </p>
          </div>
        </div>
      )}

      {/* ── Evolution & AI Preview ────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-10">
        <div className="card flex flex-col justify-between p-8">
          <div>
            <h2 className="text-sm font-black uppercase tracking-widest text-text-tertiary mb-4">Evolution Preview</h2>
            <div className="text-xl font-bold leading-tight mb-6 text-text-primary">
              Repository chronologically mapped across key developmental milestones and refactoring phases.
            </div>
            <div className="flex items-center gap-4 text-xs font-mono text-text-secondary mb-8">
              <span>● Setup</span>
              <span className="flex-1 border-t-2 border-dashed border-border/30"></span>
              <span>● Refactor</span>
              <span className="flex-1 border-t-2 border-dashed border-border/30"></span>
              <span>● Expansion</span>
            </div>
          </div>
          <Link to={`/repository/${id}/evolution`} className="btn btn-secondary self-start w-full sm:w-auto">
            View Full Evolution →
          </Link>
        </div>

        <div className="card flex flex-col justify-between p-8 border-2 border-[var(--color-border)] shadow-hard">
          <div>
            <h2 className="text-sm font-black uppercase tracking-widest text-[var(--color-text-tertiary)] mb-4">AI Summary Preview</h2>
            <div className="text-lg font-medium leading-relaxed mb-8 text-[var(--color-text-primary)]">
              {truncatedAI ? (
                <span>{truncatedAI}</span>
              ) : (
                <span className="text-[var(--color-text-secondary)] italic">AI insights haven't been generated yet.</span>
              )}
            </div>
          </div>
          <Link to={`/repository/${id}/ai`} className="btn btn-secondary self-start w-full sm:w-auto">
            {truncatedAI ? "Read Full AI Summary →" : "Explore AI Insights →"}
          </Link>
        </div>
      </div>

      {/* ── Architecture Preview ────────────────────────── */}
      <div className="mb-10">
        <div className="card p-8 border-l-8 border-l-info">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6">
            <div>
               <h2 className="text-sm font-black uppercase tracking-widest text-text-tertiary mb-3">Architecture Preview</h2>
               <p className="text-xl font-bold text-text-primary">
                 Explore structural shifts, module coupling, and architectural heatmaps.
               </p>
            </div>
            <Link to={`/repository/${id}/architecture`} className="btn btn-secondary whitespace-nowrap">
              Explore Architecture →
            </Link>
          </div>
        </div>
      </div>

      {/* ── Hotspots & Contributors ────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Top Hotspots */}
        <div className="card p-8 flex flex-col">
          <h2 className="text-sm font-black uppercase tracking-widest text-text-tertiary mb-6">Top Hotspots</h2>
          <div className="flex-1 flex flex-col space-y-4 mb-8">
            {topActive.length === 0 ? (
              <div className="flex-1 flex items-center justify-center">
                <p className="text-sm text-text-tertiary italic">No hotspot data available.</p>
              </div>
            ) : (
              topActive.map((file, idx) => (
                <div key={idx} className="flex items-center justify-between border-b-2 border-border/10 pb-3">
                  <div className="text-sm font-mono font-medium truncate max-w-[60%]">{file.file_path}</div>
                  <div className="text-xs font-bold bg-warning/20 text-warning px-2 py-1 uppercase">{file.commits_count} Commits</div>
                </div>
              ))
            )}
          </div>
          <Link to={`/repository/${id}/hotspots`} className="btn btn-secondary w-full">
            View All Hotspots →
          </Link>
        </div>

        {/* Top Contributors */}
        <div className="card p-8 flex flex-col">
          <h2 className="text-sm font-black uppercase tracking-widest text-text-tertiary mb-6 flex justify-between items-center">
            Top Contributors
            <span className={`px-2 py-1 text-[10px] ${isHealthy ? 'bg-success/20 text-success' : 'bg-warning/20 text-warning'}`}>
              Bus Factor: {busFactor?.repo_bus_factor || "?"}
            </span>
          </h2>
          <div className="flex-1 flex flex-col space-y-4 mb-8">
            {topContributors.length === 0 ? (
              <div className="flex-1 flex items-center justify-center">
                <p className="text-sm text-text-tertiary italic">No contributor data available.</p>
              </div>
            ) : (
              topContributors.map(([author, count], idx) => {
                const total = Object.values(busFactor.top_contributors).reduce((s, v) => s + v, 0) || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={idx} className="flex items-center justify-between border-b-2 border-border/10 pb-3">
                    <div className="text-sm font-medium truncate">{author}</div>
                    <div className="flex items-center gap-3">
                       <span className="text-xs text-text-secondary font-mono">{pct}%</span>
                       <span className="text-[10px] uppercase font-bold bg-border/5 px-2 py-1">{count} Commits</span>
                    </div>
                  </div>
                )
              })
            )}
          </div>
          <Link to={`/repository/${id}/contributors`} className="btn btn-secondary w-full">
            View Contributors →
          </Link>
        </div>

      </div>
    </div>
  );
}
