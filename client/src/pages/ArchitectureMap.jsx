import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import HotspotTreemap from "../components/HotspotTreemap";

const COMMIT_TYPE_OPTIONS = [
  { value: "all", label: "All Types" },
  { value: "feat", label: "✨ feat" },
  { value: "fix", label: "🐛 fix" },
  { value: "refactor", label: "♻️ refactor" },
  { value: "docs", label: "📝 docs" },
  { value: "test", label: "🧪 test" },
  { value: "chore", label: "🔧 chore" },
  { value: "perf", label: "⚡ perf" },
  { value: "style", label: "💄 style" },
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

export default function ArchitectureMap() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [hotspots, setHotspots] = useState([]);
  const [couplingData, setCouplingData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [activeTab, setActiveTab] = useState("active");
  const [selectedPreset, setSelectedPreset] = useState(0); // index into DATE_PRESETS
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
      const [hotspotsData, coupling] = await Promise.all([
        api.get(`/api/analytics/${id}/hotspots${queryStr}`),
        api.get(`/api/analytics/${id}/temporal-coupling`),
      ]);

      setHotspots(hotspotsData || []);
      setCouplingData(coupling || []);
    } catch (err) {
      setError(err.message || "Failed to load architecture map data");
    } finally {
      setLoading(false);
    }
  }, [id, selectedPreset, selectedCommitType]);

  useEffect(() => { loadData(); }, [loadData]);

  const activeHotspots = hotspots.filter(h => !h.is_deleted);
  const historicalHotspots = hotspots.filter(h => h.is_deleted);
  const currentHotspots = activeTab === "active" ? activeHotspots : historicalHotspots;

  // CSV Export: hotspots
  const handleExportHotspotsCSV = () => {
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

  // CSV Export: coupling
  const handleExportCouplingCSV = () => {
    if (!couplingData.length) return;
    const headers = ["file_a", "file_b", "co_changes", "degree"];
    const rows = couplingData.map(c => [`"${c.file_a}"`, `"${c.file_b}"`, c.co_changes, c.degree]);
    const csv = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `gitcompass_coupling_${id}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  if (loading) {
    return (
      <div className="card-flat p-12 text-center text-text-secondary animate-pulse-soft">
        Loading architecture map…
      </div>
    );
  }

  if (error) {
    return (
      <div className="card-flat p-12 text-center text-error bg-error-light">
        <p className="font-medium">Error loading architecture map</p>
        <p className="text-sm mt-1">{error}</p>
        <Link to={`/repository/${id}`} className="text-primary-600 text-sm mt-4 inline-block underline">
          ← Back to Repository Analytics
        </Link>
      </div>
    );
  }

  if (!repo) return null;

  return (
    <div className="animate-fade-in pb-12">
      {/* ── Breadcrumbs & Header ────────────────────────── */}
      <div className="mb-6 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-sm text-text-tertiary mb-3 flex-wrap">
            <Link to="/" className="hover:text-text-primary transition-colors">Dashboard</Link>
            <span>/</span>
            <Link to={`/repository/${id}`} className="hover:text-text-primary transition-colors">
              {repo.name || "Analytics"}
            </Link>
            <span>/</span>
            <span className="text-text-primary font-medium">Architecture Map</span>
          </div>

          <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
            {repo.name || repo.github_url} — Architecture Map
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Visual structural decomposition, code churn heatmap &amp; temporal coupling analysis
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap self-start sm:self-auto">
          <button
            onClick={handleExportHotspotsCSV}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-raised border border-border text-text-primary text-xs font-medium hover:bg-surface-hover transition-colors shadow-2xs cursor-pointer"
          >
            <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Hotspots CSV
          </button>
          <button
            onClick={handleExportCouplingCSV}
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-raised border border-border text-text-primary text-xs font-medium hover:bg-surface-hover transition-colors shadow-2xs cursor-pointer"
          >
            <svg className="w-4 h-4 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            Export Coupling CSV
          </button>
          <Link
            to={`/repository/${id}`}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-raised border border-border text-text-primary text-sm font-medium hover:bg-surface-hover transition-colors shadow-2xs"
          >
            <svg className="w-4 h-4 text-text-secondary" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Analytics
          </Link>
        </div>
      </div>

      {/* ── Filters: Time Machine & Commit Type ─────────── */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        {/* Time Machine */}
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

        {/* Commit Type Pills */}
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

      {/* ── Architecture Treemap ────────────────────────── */}
      <HotspotTreemap hotspots={currentHotspots} couplingData={couplingData} />

      {/* ── Temporal Coupling Table ─────────────────────── */}
      {couplingData.length > 0 && (
        <div className="mt-10">
          <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
            <svg className="w-5 h-5 text-cyan-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
            Top Temporal Couplings
            <span className="text-xs font-normal text-text-tertiary ml-2">({couplingData.length} pairs found)</span>
          </h2>
          <div className="card-flat overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-surface-raised">
                    <th className="text-left px-4 py-3 text-text-tertiary font-semibold text-xs uppercase tracking-wide">File A</th>
                    <th className="text-left px-4 py-3 text-text-tertiary font-semibold text-xs uppercase tracking-wide">File B</th>
                    <th className="text-center px-4 py-3 text-text-tertiary font-semibold text-xs uppercase tracking-wide">Co-Changes</th>
                    <th className="text-center px-4 py-3 text-text-tertiary font-semibold text-xs uppercase tracking-wide">Coupling Degree</th>
                  </tr>
                </thead>
                <tbody>
                  {couplingData.slice(0, 20).map((item, i) => (
                    <tr key={i} className="border-b border-border/50 hover:bg-surface-hover transition-colors">
                      <td className="px-4 py-2.5 text-text-primary font-mono text-xs truncate max-w-[280px]">{item.file_a}</td>
                      <td className="px-4 py-2.5 text-text-primary font-mono text-xs truncate max-w-[280px]">{item.file_b}</td>
                      <td className="px-4 py-2.5 text-center">
                        <span className="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-700">{item.co_changes}</span>
                      </td>
                      <td className="px-4 py-2.5 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                          item.degree >= 0.9 ? "bg-rose-100 text-rose-700" :
                          item.degree >= 0.7 ? "bg-orange-100 text-orange-700" :
                          "bg-cyan-100 text-cyan-700"
                        }`}>
                          {Math.round(item.degree * 100)}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
