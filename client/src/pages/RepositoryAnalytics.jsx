/**
 * RepositoryAnalytics — Phase 4.5 Deep Architectural Analytics.
 *
 * Features: Hotspot table, Bus Factor cards, Orphan Risk files,
 * Commit Type breakdown, Time Machine filter, CSV export.
 */

import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import AISummaryCard from "../components/AISummaryCard";
import ArchitectureTimeline from "../components/ArchitectureTimeline";
import QAChatAssistant from "../components/QAChatAssistant";
import AIVibeMeter from "../components/AIVibeMeter";

const COMMIT_TYPE_OPTIONS = [
  { value: "all", label: "All Types" },
  { value: "feat", label: "✨ feat" },
  { value: "fix", label: "🐛 fix" },
  { value: "refactor", label: "♻️ refactor" },
  { value: "docs", label: "📝 docs" },
  { value: "test", label: "🧪 test" },
  { value: "chore", label: "🔧 chore" },
  { value: "perf", label: "⚡ perf" },
];

const DATE_PRESETS = [
  { label: "All Time", value: null },
  { label: "Last 30 Days", days: 30 },
  { label: "Last 90 Days", days: 90 },
  { label: "Last 6 Months", days: 180 },
  { label: "Last Year", days: 365 },
];

function isoDateDaysAgo(days) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString();
}

const COMMIT_TYPE_COLORS = {
  feat: "bg-emerald-100 text-emerald-700",
  fix: "bg-rose-100 text-rose-700",
  refactor: "bg-purple-100 text-purple-700",
  docs: "bg-blue-100 text-blue-700",
  test: "bg-amber-100 text-amber-700",
  chore: "bg-slate-100 text-slate-600",
  perf: "bg-cyan-100 text-cyan-700",
  style: "bg-pink-100 text-pink-700",
  ci: "bg-orange-100 text-orange-700",
  build: "bg-indigo-100 text-indigo-700",
  revert: "bg-red-100 text-red-700",
  other: "bg-gray-100 text-gray-600",
};

export default function RepositoryAnalytics() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [summary, setSummary] = useState(null);
  const [busFactor, setBusFactor] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Sorting state
  const [sortField, setSortField] = useState("commits_count");
  const [sortOrder, setSortOrder] = useState("desc");

  // Tab state
  const [activeTab, setActiveTab] = useState("active");

  // Filters
  const [selectedPreset, setSelectedPreset] = useState(0);
  const [selectedCommitType, setSelectedCommitType] = useState("all");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const repoData = await api.get(`/api/repositories/${id}`);
      setRepo(repoData);

      const preset = DATE_PRESETS[selectedPreset];
      const params = new URLSearchParams();
      if (preset?.days) params.set("start_date", isoDateDaysAgo(preset.days));
      if (selectedCommitType && selectedCommitType !== "all") params.set("commit_type", selectedCommitType);
      const queryStr = params.toString() ? `?${params.toString()}` : "";

      const [hotspotsData, summaryData, busFactorData] = await Promise.all([
        api.get(`/api/analytics/${id}/hotspots${queryStr}`),
        api.get(`/api/analytics/${id}/summary`).catch(() => null),
        api.get(`/api/analytics/${id}/bus-factor`).catch(() => null),
      ]);

      setHotspots(hotspotsData || []);
      setSummary(summaryData);
      setBusFactor(busFactorData);
    } catch (err) {
      setError(err.message || "Failed to load analytics");
    } finally {
      setLoading(false);
    }
  }, [id, selectedPreset, selectedCommitType]);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortOrder("desc");
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

  // CSV Export
  const handleExportCSV = () => {
    if (!hotspots.length) return;
    const headers = ["file_path", "commits_count", "total_insertions", "total_deletions", "authors", "top_author", "top_author_share", "is_orphan_risk", "is_deleted"];
    const rows = hotspots.map(h => [
      `"${h.file_path}"`,
      h.commits_count,
      h.total_insertions,
      h.total_deletions,
      `"${(h.authors || []).join("; ")}"`,
      `"${h.top_author || ""}"`,
      h.top_author_share || 0,
      h.is_orphan_risk ? "Yes" : "No",
      h.is_deleted ? "Yes" : "No",
    ]);
    const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `gitcompass_hotspots_${id}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

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
          ← Back to Dashboard
        </Link>
      </div>
    );
  }

  if (!repo) return null;

  const commitTypeDist = summary?.commit_types_distribution || {};
  const totalTypedCommits = Object.values(commitTypeDist).reduce((s, v) => s + v, 0) || 1;

  return (
    <div className="animate-fade-in pb-12">
      {/* ── Breadcrumbs & Header ────────────────────────── */}
      <div className="mb-8 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
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
          <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
            {repo.name || repo.github_url}
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Codebase Hotspots &amp; Deep Architectural Analytics
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap self-start sm:self-auto">
          <button
            onClick={handleExportCSV}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-raised border border-border text-text-primary text-xs font-medium hover:bg-surface-hover transition-colors shadow-2xs cursor-pointer"
          >
            <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export CSV
          </button>
          <Link
            to={`/repository/${id}/architecture`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700 transition-colors shadow-sm"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z" />
            </svg>
            View Architecture Map
          </Link>
        </div>
      </div>

      {/* ── Summary Cards ────────────────────────────────── */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
          <div className="card-flat p-4">
            <p className="text-xs text-text-tertiary font-semibold uppercase tracking-wide">Total Files</p>
            <p className="text-2xl font-bold text-text-primary mt-1">{summary.total_files.toLocaleString()}</p>
          </div>
          <div className="card-flat p-4">
            <p className="text-xs text-text-tertiary font-semibold uppercase tracking-wide">Bus Factor</p>
            <p className={`text-2xl font-bold mt-1 ${summary.bus_factor <= 2 ? "text-rose-600" : summary.bus_factor <= 4 ? "text-amber-600" : "text-emerald-600"}`}>
              {summary.bus_factor}
            </p>
            <p className="text-[10px] text-text-tertiary mt-0.5">{summary.bus_factor <= 2 ? "⚠ High Risk" : summary.bus_factor <= 4 ? "Moderate" : "Healthy"}</p>
          </div>
          <div className="card-flat p-4">
            <p className="text-xs text-text-tertiary font-semibold uppercase tracking-wide">Orphan Risk Files</p>
            <p className={`text-2xl font-bold mt-1 ${summary.orphan_files_count > 10 ? "text-rose-600" : "text-amber-600"}`}>
              {summary.orphan_files_count}
            </p>
          </div>
          <div className="card-flat p-4">
            <p className="text-xs text-text-tertiary font-semibold uppercase tracking-wide">Coupled Pairs</p>
            <p className="text-2xl font-bold text-text-primary mt-1">{summary.total_coupled_pairs}</p>
          </div>
          <div className="card-flat p-4">
            <p className="text-xs text-text-tertiary font-semibold uppercase tracking-wide">Sampled Commits</p>
            <p className="text-2xl font-bold text-text-primary mt-1">{(summary.total_commits || 0).toLocaleString()}</p>
          </div>
        </div>
      )}

      {/* ── AI Insights (Phase 5) ────────────────────────── */}
      <div className="mb-8 space-y-4">
        <h2 className="text-lg font-semibold text-text-primary flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
          </svg>
          AI Architectural Insights
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <AISummaryCard repoId={id} />
            <ArchitectureTimeline repoId={id} />
          </div>
          <div className="lg:col-span-1">
            <QAChatAssistant repoId={id} />
            <AIVibeMeter repoId={id} />
          </div>
        </div>
      </div>

      {/* ── Commit Type Breakdown ────────────────────────── */}
      {Object.keys(commitTypeDist).length > 0 && (
        <div className="card-flat p-5 mb-8">
          <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
            <svg className="w-4 h-4 text-purple-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
            </svg>
            Commit Type Breakdown
          </h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(commitTypeDist)
              .sort((a, b) => b[1] - a[1])
              .map(([type, count]) => (
                <div key={type} className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold border ${COMMIT_TYPE_COLORS[type] || "bg-gray-100 text-gray-600"} border-transparent`}>
                  <span className="capitalize">{type}</span>
                  <span className="opacity-70">{count}</span>
                  <span className="opacity-50">({Math.round((count / totalTypedCommits) * 100)}%)</span>
                </div>
              ))}
          </div>
        </div>
      )}

      {/* ── Bus Factor & Orphan Risk ─────────────────────── */}
      {busFactor && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Top Contributors */}
          <div className="card-flat p-5">
            <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
              Top Contributors
              <span className={`ml-2 px-2 py-0.5 rounded-full text-[10px] font-bold ${busFactor.repo_bus_factor <= 2 ? "bg-rose-100 text-rose-700" : busFactor.repo_bus_factor <= 4 ? "bg-amber-100 text-amber-700" : "bg-emerald-100 text-emerald-700"}`}>
                Bus Factor: {busFactor.repo_bus_factor}
              </span>
            </h2>
            <div className="space-y-2">
              {Object.entries(busFactor.top_contributors || {}).slice(0, 8).map(([author, count]) => {
                const total = Object.values(busFactor.top_contributors).reduce((s, v) => s + v, 0) || 1;
                const pct = Math.round((count / total) * 100);
                return (
                  <div key={author} className="flex items-center gap-3">
                    <div className="w-6 h-6 rounded-full bg-primary-100 flex items-center justify-center text-[10px] font-bold text-primary-700 shrink-0">
                      {author.slice(0, 1).toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-text-primary font-medium truncate">{author}</span>
                        <span className="text-text-tertiary shrink-0 ml-2">{pct}%</span>
                      </div>
                      <div className="h-1.5 bg-surface-hover rounded-full overflow-hidden">
                        <div className="h-full bg-primary-500 rounded-full transition-all" style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Orphan Risk Files */}
          <div className="card-flat p-5">
            <h2 className="text-sm font-semibold text-text-primary mb-4 flex items-center gap-2">
              <svg className="w-4 h-4 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              Knowledge Loss — Orphan Risk Files
              <span className="ml-auto text-[10px] font-normal text-text-tertiary">≥80% single-owner or stale &gt;90 days</span>
            </h2>
            {busFactor.orphan_risk_files?.length === 0 ? (
              <p className="text-sm text-text-tertiary italic">No orphan risk files detected. Great ownership spread!</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {(busFactor.orphan_risk_files || []).slice(0, 15).map((f, i) => (
                  <div key={i} className="flex items-center justify-between gap-3 py-1.5 border-b border-border/50">
                    <span className="text-xs font-mono text-text-primary truncate max-w-[65%]">{f.file_path}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] text-text-tertiary">{f.top_author}</span>
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-700">
                        {Math.round((f.top_author_share || 0) * 100)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ── Filters: Time Machine & Commit Type ─────────── */}
      <div className="mb-5 flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wide">Time Machine</span>
          <div className="flex gap-1 flex-wrap">
            {DATE_PRESETS.map((preset, idx) => (
              <button
                key={idx}
                onClick={() => setSelectedPreset(idx)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  selectedPreset === idx
                    ? "bg-primary-600 text-white border-primary-700 shadow-xs"
                    : "bg-surface-raised border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                }`}
              >
                {preset.label}
              </button>
            ))}
          </div>
        </div>

        <div className="hidden sm:block w-px h-10 bg-border" />

        <div className="flex flex-col gap-1">
          <span className="text-xs font-semibold text-text-tertiary uppercase tracking-wide">Commit Type</span>
          <div className="flex gap-1 flex-wrap">
            {COMMIT_TYPE_OPTIONS.map(opt => (
              <button
                key={opt.value}
                onClick={() => setSelectedCommitType(opt.value)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                  selectedCommitType === opt.value
                    ? "bg-primary-600 text-white border-primary-700 shadow-xs"
                    : "bg-surface-raised border-border text-text-secondary hover:text-text-primary hover:bg-surface-hover"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Tabs ────────────────────────────────────────── */}
      <div className="flex gap-4 border-b border-border mb-6 px-2">
        <button
          onClick={() => setActiveTab("active")}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === "active"
              ? "border-primary-500 text-primary-600 font-semibold"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          Active Files ({activeHotspots.length})
        </button>
        <button
          onClick={() => setActiveTab("historical")}
          className={`pb-3 text-sm font-medium transition-colors border-b-2 ${
            activeTab === "historical"
              ? "border-primary-500 text-primary-600 font-semibold"
              : "border-transparent text-text-secondary hover:text-text-primary"
          }`}
        >
          Historical Files ({historicalHotspots.length})
        </button>
      </div>

      {/* ── Hotspot Table ───────────────────────────────── */}
      <div className="card-flat overflow-hidden">
        <div className="px-6 py-4 border-b border-border bg-surface-hover/50">
          <h2 className="text-sm font-semibold text-text-primary">
            {activeTab === "active" ? "Most Volatile Active Files" : "Most Volatile Historical Files (Deleted)"}
          </h2>
          <p className="text-xs text-text-tertiary mt-0.5">
            {activeTab === "active"
              ? "Files currently present, ranked by churn. Hover commit type badges for type breakdown."
              : "Deleted files with significant historical churn."}
          </p>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-surface-hover/30 border-b border-border">
                <th className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide">File Path</th>
                <th
                  className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide cursor-pointer hover:bg-surface-hover/50 select-none transition-colors"
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
                  className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide cursor-pointer hover:bg-surface-hover/50 select-none transition-colors"
                  onClick={() => handleSort("total_volume")}
                >
                  <div className="flex items-center gap-1">
                    Volume (Lines)
                    {sortField === "total_volume" && (
                      <span className="text-primary-500">{sortOrder === "asc" ? "↑" : "↓"}</span>
                    )}
                  </div>
                </th>
                <th className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide">Ownership</th>
                <th className="px-6 py-3 text-xs font-semibold text-text-secondary tracking-wide">Risk</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {sortedHotspots.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-text-tertiary text-sm">
                    No analytics data found for this repository.
                  </td>
                </tr>
              ) : (
                sortedHotspots.map((hotspot) => (
                  <tr key={hotspot.file_path} className="hover:bg-surface-hover/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="text-sm font-medium text-text-primary break-all max-w-[280px]">
                        {hotspot.file_path}
                      </div>
                      {/* Commit type breakdown mini-badges */}
                      {hotspot.commit_types && Object.keys(hotspot.commit_types).length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {Object.entries(hotspot.commit_types)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 4)
                            .map(([type, count]) => (
                              <span
                                key={type}
                                className={`px-1.5 py-0.5 rounded text-[9px] font-semibold ${COMMIT_TYPE_COLORS[type] || "bg-gray-100 text-gray-600"}`}
                                title={`${type}: ${count} commits`}
                              >
                                {type} {count}
                              </span>
                            ))}
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-error-light text-error">
                        {hotspot.commits_count} commits
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3 text-xs font-medium">
                        <span className="text-success" title="Insertions">+{hotspot.total_insertions.toLocaleString()}</span>
                        <span className="text-error" title="Deletions">-{hotspot.total_deletions.toLocaleString()}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {hotspot.top_author ? (
                        <div>
                          <div className="text-xs font-semibold text-text-primary truncate max-w-[120px]">{hotspot.top_author}</div>
                          <div className="text-[10px] text-text-tertiary mt-0.5">{Math.round((hotspot.top_author_share || 0) * 100)}% ownership</div>
                        </div>
                      ) : (
                        <span className="text-text-tertiary text-xs">—</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {hotspot.is_orphan_risk ? (
                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-bold bg-rose-100 text-rose-700 border border-rose-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                          Orphan Risk
                        </span>
                      ) : (
                        <span className="text-[10px] text-emerald-600 font-medium">✓ Healthy</span>
                      )}
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
