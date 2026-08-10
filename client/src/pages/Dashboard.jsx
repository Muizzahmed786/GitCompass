/**
 * Dashboard — Repository Management & Analysis View.
 *
 * Provides functionality to:
 * - View API health status
 * - Track aggregated metrics (repos, commits, files)
 * - Add new GitHub repositories for analysis via POST /api/repositories
 * - Display live status updates (auto-polling pending/cloning/mining jobs)
 * - Delete repositories
 */

import { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import StatusBadge from "../components/StatusBadge";

export default function Dashboard({ user }) {
  const [healthStatus, setHealthStatus] = useState("loading");
  const [repositories, setRepositories] = useState([]);
  const [loadingRepos, setLoadingRepos] = useState(true);

  // Form state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newRepoUrl, setNewRepoUrl] = useState("");
  const [newRepoBranch, setNewRepoBranch] = useState("");
  const [availableBranches, setAvailableBranches] = useState([]);
  const [fetchingBranches, setFetchingBranches] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState(null);

  const pollTimerRef = useRef(null);

  useEffect(() => {
    checkHealth();
    loadRepositories();

    return () => {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
      }
    };
  }, []);

  // Fetch branches when URL changes
  useEffect(() => {
    const fetchBranches = async () => {
      const match = newRepoUrl.match(/github\.com\/([^/]+)\/([^/.]+)(?:\.git)?/);
      if (match) {
        const owner = match[1];
        const repo = match[2];
        setFetchingBranches(true);
        try {
          const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/branches`);
          if (res.ok) {
            const data = await res.json();
            setAvailableBranches(data.map(b => b.name));
          } else {
            setAvailableBranches([]);
          }
        } catch (e) {
          setAvailableBranches([]);
        } finally {
          setFetchingBranches(false);
        }
      } else {
        setAvailableBranches([]);
      }
    };

    const timer = setTimeout(fetchBranches, 500);
    return () => clearTimeout(timer);
  }, [newRepoUrl]);

  // Set up auto-polling if any repository is actively mining
  useEffect(() => {
    const hasActiveMining = repositories.some((r) =>
      ["pending", "cloning", "mining"].includes(r.status)
    );

    if (hasActiveMining) {
      if (!pollTimerRef.current) {
        pollTimerRef.current = setInterval(() => {
          loadRepositories(true);
        }, 3000);
      }
    } else {
      if (pollTimerRef.current) {
        clearInterval(pollTimerRef.current);
        pollTimerRef.current = null;
      }
    }
  }, [repositories]);

  const checkHealth = async () => {
    try {
      const data = await api.get("/api/health");
      setHealthStatus(data.status === "ok" ? "ok" : "degraded");
    } catch {
      setHealthStatus("error");
    }
  };

  const loadRepositories = async (isSilent = false) => {
    if (!isSilent) setLoadingRepos(true);
    try {
      const data = await api.get("/api/repositories");
      setRepositories(data.repositories || []);
    } catch (err) {
      console.error("Failed to load repositories:", err);
    } finally {
      if (!isSilent) setLoadingRepos(false);
    }
  };

  const handleAddRepository = async (e) => {
    e.preventDefault();
    setFormError(null);

    const trimmed = newRepoUrl.trim();
    if (!trimmed) {
      setFormError("Please enter a valid GitHub URL.");
      return;
    }

    setSubmitting(true);
    try {
      await api.post("/api/repositories", { 
        github_url: trimmed,
        branch: newRepoBranch.trim() || undefined
      });
      setNewRepoUrl("");
      setNewRepoBranch("");
      setShowAddModal(false);
      await loadRepositories();
    } catch (err) {
      setFormError(err.message || "Failed to add repository.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleRetryRepository = async (repo) => {
    try {
      await api.post("/api/repositories", { 
        github_url: repo.github_url,
        branch: repo.default_branch || undefined
      });
      await loadRepositories();
    } catch (err) {
      alert(`Failed to retry repository: ${err.message}`);
    }
  };

  const handleDeleteRepository = async (repoId, repoName) => {
    if (
      !window.confirm(
        `Are you sure you want to delete "${repoName || repoId}"? All parsed commits and diff data will be removed.`
      )
    ) {
      return;
    }

    try {
      await api.delete(`/api/repositories/${repoId}`);
      setRepositories((prev) => prev.filter((r) => r.id !== repoId));
    } catch (err) {
      alert(`Failed to delete repository: ${err.message}`);
    }
  };

  const displayName =
    user?.user_metadata?.full_name ||
    user?.user_metadata?.user_name ||
    "there";

  // Calculate high-level aggregates
  const totalCommits = repositories.reduce(
    (acc, r) => acc + (r.total_commits || 0),
    0
  );
  const totalFiles = repositories.reduce(
    (acc, r) => acc + (r.total_files || 0),
    0
  );

  return (
    <div className="animate-fade-in">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary tracking-tight">
            Welcome, {displayName}
          </h1>
          <p className="mt-1 text-sm text-text-secondary">
            Your repository analysis dashboard
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-text-tertiary">API Status</span>
          <StatusBadge status={healthStatus} />
        </div>
      </div>

      {/* ── Metric Cards ───────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8 stagger-children">
        <div className="card-flat p-5">
          <p className="text-xs font-medium text-text-tertiary uppercase tracking-wider">
            Repositories
          </p>
          <p className="mt-2 text-3xl font-semibold text-text-primary">
            {repositories.length}
          </p>
        </div>
        <div className="card-flat p-5">
          <p className="text-xs font-medium text-text-tertiary uppercase tracking-wider">
            Total Commits
          </p>
          <p className="mt-2 text-3xl font-semibold text-text-primary">
            {totalCommits.toLocaleString()}
          </p>
        </div>
        <div className="card-flat p-5">
          <p className="text-xs font-medium text-text-tertiary uppercase tracking-wider">
            Files Tracked
          </p>
          <p className="mt-2 text-3xl font-semibold text-text-primary">
            {totalFiles.toLocaleString()}
          </p>
        </div>
      </div>

      {/* ── Action Header & Add Modal Trigger ──────────── */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-semibold text-text-primary">
            Analyzed Repositories
          </h2>
          <p className="text-xs text-text-secondary">
            Git history intelligence & churn metrics
          </p>
        </div>

        <button
          onClick={() => {
            setShowAddModal(true);
            setFormError(null);
          }}
          className="
            inline-flex items-center gap-2
            px-4 py-2 rounded-lg
            bg-primary-600 text-white text-sm font-medium
            hover:bg-primary-700
            transition-colors duration-150
            cursor-pointer shadow-sm
          "
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M12 4.5v15m7.5-7.5h-15"
            />
          </svg>
          Add Repository
        </button>
      </div>

      {/* ── Add Repository Modal ───────────────────────── */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/30 backdrop-blur-xs animate-fade-in">
          <div className="bg-surface-raised border border-border rounded-2xl max-w-md w-full p-6 shadow-elevated">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">
                Analyze a Repository
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-text-tertiary hover:text-text-primary p-1 rounded-lg hover:bg-surface-hover cursor-pointer"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleAddRepository}>
              <div className="mb-4">
                <label className="block text-xs font-medium text-text-secondary uppercase tracking-wider mb-2">
                  GitHub Repository URL
                </label>
                  <div className="flex flex-col sm:flex-row gap-3">
                    <input
                      type="url"
                      required
                      value={newRepoUrl}
                      onChange={(e) => setNewRepoUrl(e.target.value)}
                      placeholder="e.g. https://github.com/facebook/react"
                      className="w-full px-3.5 py-2.5 rounded-lg border border-border bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all duration-150"
                      disabled={submitting}
                    />
                    {availableBranches.length > 0 ? (
                      <select
                        value={newRepoBranch}
                        onChange={(e) => setNewRepoBranch(e.target.value)}
                        className="w-full sm:w-48 px-3.5 py-2.5 rounded-lg border border-border bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all duration-150"
                        disabled={submitting}
                      >
                        <option value="">Default branch</option>
                        {availableBranches.map(branch => (
                          <option key={branch} value={branch}>{branch}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        value={newRepoBranch}
                        onChange={(e) => setNewRepoBranch(e.target.value)}
                        placeholder={fetchingBranches ? "Loading branches..." : "Branch (e.g. main)"}
                        className="w-full sm:w-48 px-3.5 py-2.5 rounded-lg border border-border bg-surface text-text-primary text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500 transition-all duration-150"
                        disabled={submitting || fetchingBranches}
                      />
                    )}
                  </div>
                  <p className="mt-2 text-xs text-text-tertiary">
                    Enter a public GitHub repository URL. The optional branch defaults to the primary branch. 
                    If this repository is already tracked, it will be wiped and re-mined!
                  </p>
              </div>

              {formError && (
                <div className="mb-4 p-3 rounded-lg bg-error-light text-error text-xs">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-3">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg text-sm text-text-secondary hover:text-text-primary hover:bg-surface-hover cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="
                    px-4 py-2 rounded-lg text-sm font-medium text-white
                    bg-primary-600 hover:bg-primary-700
                    disabled:opacity-50 disabled:cursor-not-allowed
                    transition-colors duration-150 cursor-pointer
                  "
                >
                  {submitting ? "Starting Mine…" : "Mine Repository"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Repositories List ──────────────────────────── */}
      {loadingRepos ? (
        <div className="card-flat p-12 text-center text-text-secondary animate-pulse-soft">
          Loading repositories…
        </div>
      ) : repositories.length === 0 ? (
        /* Empty State */
        <div className="card p-10 text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-primary-50 rounded-xl mb-4">
            <svg
              className="w-6 h-6 text-primary-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 4.5v15m7.5-7.5h-15"
              />
            </svg>
          </div>
          <h3 className="text-base font-semibold text-text-primary">
            No repositories analyzed yet
          </h3>
          <p className="mt-1 text-sm text-text-secondary max-w-sm mx-auto">
            Click the button below to add your first GitHub repository URL and begin mining.
          </p>
          <button
            onClick={() => {
              setShowAddModal(true);
              setFormError(null);
            }}
            className="
              mt-5 inline-flex items-center gap-2
              px-4 py-2 rounded-lg
              bg-primary-600 text-white text-sm font-medium
              hover:bg-primary-700
              transition-colors duration-150 cursor-pointer shadow-sm
            "
          >
            Add Repository
          </button>
        </div>
      ) : (
        /* Repository Cards */
        <div className="grid grid-cols-1 gap-4">
          {repositories.map((repo) => (
            <div
              key={repo.id}
              className="card p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="text-base font-semibold text-text-primary group-hover:text-primary-600 transition-colors">
                      {repo.name || "Unknown Repository"}
                    </h3>
                    {repo.default_branch && (
                      <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-surface text-text-secondary border border-border uppercase tracking-wide">
                        {repo.default_branch}
                      </span>
                    )}
                  </div>
                  <StatusBadge status={repo.status} />
                </div>

                <a
                  href={repo.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-text-tertiary hover:text-primary-600 transition-colors"
                >
                  {repo.github_url}
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>

                {repo.error_message && (
                  <p className="text-xs text-error mt-1 bg-error-light p-2 rounded-md">
                    Error: {repo.error_message}
                  </p>
                )}
              </div>

              <div className="flex items-center gap-6 sm:gap-8">
                <div className="text-right">
                  <p className="text-xs text-text-tertiary uppercase tracking-wider">Commits</p>
                  <p className="text-sm font-semibold text-text-primary">
                    {repo.total_commits ? repo.total_commits.toLocaleString() : "—"}
                  </p>
                </div>

                <div className="text-right">
                  <p className="text-xs text-text-tertiary uppercase tracking-wider">Files</p>
                  <p className="text-sm font-semibold text-text-primary">
                    {repo.total_files ? repo.total_files.toLocaleString() : "—"}
                  </p>
                </div>

                {repo.status === "ready" && (
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/repository/${repo.id}`}
                      className="
                        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                        bg-primary-50 text-primary-700 text-sm font-medium
                        hover:bg-primary-100 transition-colors
                      "
                    >
                      Analytics
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </Link>

                    <Link
                      to={`/repository/${repo.id}/architecture`}
                      className="
                        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg
                        bg-surface-raised border border-border text-text-primary text-sm font-medium
                        hover:bg-surface-hover transition-colors
                      "
                      title="View Repository Architecture Map"
                    >
                      Architecture Map
                    </Link>
                  </div>
                )}

                <div className="flex items-center gap-1">
                  <button
                    onClick={() => handleRetryRepository(repo)}
                    className="p-2 text-text-tertiary hover:text-primary-600 hover:bg-primary-50 rounded-lg transition-colors cursor-pointer"
                    title="Retry / Re-mine repository"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                  <button
                    onClick={() => handleDeleteRepository(repo.id, repo.name)}
                    className="p-2 text-text-tertiary hover:text-error hover:bg-error-light rounded-lg transition-colors cursor-pointer"
                    title="Delete repository"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
