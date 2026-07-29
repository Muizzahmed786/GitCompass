/**
 * RepositoryAnalytics — Detailed view of codebase hotspots.
 *
 * Displays the Churn and Contributor metrics for a specific repository.
 */

import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import HotspotTreemap from "../components/HotspotTreemap";

export default function RepositoryAnalytics() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Sorting state
  const [sortField, setSortField] = useState("commits_count"); // 'commits_count' or 'total_volume'
  const [sortOrder, setSortOrder] = useState("desc"); // 'asc' or 'desc'
  
  // Tab state
  const [activeTab, setActiveTab] = useState("active"); // 'active' or 'historical'

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const repoData = await api.get(`/api/repositories/${id}`);
        setRepo(repoData);

        const hotspotsData = await api.get(`/api/analytics/${id}/hotspots`);
        setHotspots(hotspotsData || []);
      } catch (err) {
        setError(err.message || "Failed to load analytics");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [id]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc"); // Default to desc for a new field (show worst first)
    }
  };

  const activeHotspots = hotspots.filter(h => !h.is_deleted);
  const historicalHotspots = hotspots.filter(h => h.is_deleted);
  
  const currentHotspots = activeTab === "active" ? activeHotspots : historicalHotspots;

  const sortedHotspots = [...currentHotspots].sort((a, b) => {
    let valA = a[sortField];
    let valB = b[sortField];

    if (sortField === "total_volume") {
      valA = a.total_insertions + a.total_deletions;
      valB = b.total_insertions + b.total_deletions;
    }

    if (valA < valB) return sortOrder === "asc" ? -1 : 1;
    if (valA > valB) return sortOrder === "asc" ? 1 : -1;
    return 0;
  });

  if (loading) {
    return (
      <div className="card-flat p-12 text-center text-text-secondary animate-pulse-soft">
        Loading analytics…
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-flat p-12 text-center text-error bg-error-light">
        <p className="font-medium">Error loading analytics</p>
        <p className="text-sm mt-1">{error}</p>
        <Link to="/" className="text-primary-600 text-sm mt-4 inline-block underline">
          &larr; Back to Dashboard
        </Link>
      </div>
    );
  }

  if (!repo) return null;

  return (
    <div className="animate-fade-in pb-12">
      {/* ── Breadcrumbs & Header ────────────────────────── */}
      <div className="mb-8">
        <Link
          to="/"
          className="inline-flex items-center gap-1.5 text-sm text-text-tertiary hover:text-text-primary transition-colors mb-4"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
          </svg>
          Back to Dashboard
        </Link>
        <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
          {repo.name || repo.github_url}
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Codebase Hotspots & Churn Analytics
        </p>
      </div>

      {/* ── Tabs ────────────────────────────────────────── */}
      <div className="flex gap-4 border-b border-border mb-6 px-2">
        <button
          onClick={() => setActiveTab("active")}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === "active"
              ? "border-primary-500 text-primary-600"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          Active Files ({activeHotspots.length})
        </button>
        <button
          onClick={() => setActiveTab("historical")}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === "historical"
              ? "border-primary-500 text-primary-600"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          Historical Files ({historicalHotspots.length})
        </button>
      </div>
      
      {/* ── Architecture Treemap ────────────────────────── */}
      <div className="mb-8">
        <HotspotTreemap hotspots={currentHotspots} />
      </div>

      {/* ── Hotspot Table ───────────────────────────────── */}
      <div className="card-flat overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-surface-hover/50">
          <h2 className="text-sm font-semibold text-text-primary">
            {activeTab === "active" ? "Most Volatile Active Files" : "Most Volatile Historical Files (Deleted)"}
          </h2>
          <p className="text-xs text-text-tertiary mt-0.5">
            {activeTab === "active" 
              ? "Files currently present in the repository, ranked by churn and modification volume."
              : "Files that have been deleted from the repository, but had significant historical churn."}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-hover/30 border-b border-border">
                <th className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide">
                  File Path
                </th>
                <th
                  className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide cursor-pointer hover:bg-surface-hover/50 select-none transition-colors group"
                  onClick={() => handleSort("commits_count")}
                >
                  <div className="flex items-center gap-1">
                    Churn (Commits)
                    {sortField === "commits_count" && (
                      <span className="text-primary-500">{sortOrder === "asc" ? "↑" : "↓"}</span>
                    )}
                  </div>
                </th>
                <th
                  className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide cursor-pointer hover:bg-surface-hover/50 select-none transition-colors group"
                  onClick={() => handleSort("total_volume")}
                >
                  <div className="flex items-center gap-1">
                    Volume (Lines Changed)
                    {sortField === "total_volume" && (
                      <span className="text-primary-500">{sortOrder === "asc" ? "↑" : "↓"}</span>
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide">
                  Contributors
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortedHotspots.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-text-tertiary text-sm">
                    No analytics data found for this repository.
                  </td>
                </tr>
              ) : (
                sortedHotspots.map((hotspot) => (
                  <tr
                    key={hotspot.file_path}
                    className="hover:bg-surface-hover/30 transition-colors"
                  >
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-text-primary break-all max-w-[300px] sm:max-w-[400px]">
                        {hotspot.file_path}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-error-light text-error">
                        {hotspot.commits_count} commits
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3 text-xs font-medium">
                        <span className="text-success" title="Insertions">
                          +{hotspot.total_insertions.toLocaleString()}
                        </span>
                        <span className="text-error" title="Deletions">
                          -{hotspot.total_deletions.toLocaleString()}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-wrap gap-1">
                        {hotspot.authors?.map((author) => (
                          <span
                            key={author}
                            className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-surface-hover text-text-secondary border border-border"
                            title={author}
                          >
                            {author}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
