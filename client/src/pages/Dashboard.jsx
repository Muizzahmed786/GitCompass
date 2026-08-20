import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import StatusBadge from "../components/StatusBadge";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import Badge from "../components/ui/Badge";

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

  const totalCommits = repositories.reduce((acc, r) => acc + (r.total_commits || 0), 0);
  const totalFiles = repositories.reduce((acc, r) => acc + (r.total_files || 0), 0);

  return (
    <div className="space-y-8 animate-fade-in">
      {/* ── Header ─────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 border-b-4 border-[var(--color-border)] pb-6">
        <div>
          <Badge variant="primary" className="mb-2">DASHBOARD</Badge>
          <h1 className="text-4xl font-black uppercase tracking-tight">
            Welcome, {displayName}
          </h1>
          <p className="mt-2 text-[var(--color-text-secondary)] font-medium">
            Your repository analysis overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs font-bold uppercase tracking-widest text-[var(--color-text-tertiary)]">API Status</span>
          <StatusBadge status={healthStatus} />
        </div>
      </div>

      {/* ── Metric Cards ───────────────────────────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="panel border-4">
          <p className="text-xs font-black uppercase tracking-widest text-[var(--color-text-tertiary)] mb-2">Repositories</p>
          <p className="text-5xl font-black">{repositories.length}</p>
        </div>
        <div className="panel border-4">
          <p className="text-xs font-black uppercase tracking-widest text-[var(--color-text-tertiary)] mb-2">Total Commits</p>
          <p className="text-5xl font-black">{totalCommits.toLocaleString()}</p>
        </div>
        <div className="panel border-4">
          <p className="text-xs font-black uppercase tracking-widest text-[var(--color-text-tertiary)] mb-2">Files Tracked</p>
          <p className="text-5xl font-black">{totalFiles.toLocaleString()}</p>
        </div>
      </div>

      {/* ── Action Header ──────────────────────────── */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 bg-[var(--color-surface-raised)] border-4 border-[var(--color-border)] p-6 shadow-hard">
        <div>
          <h2 className="text-2xl font-black uppercase">Analyzed Repositories</h2>
          <p className="text-sm font-medium text-[var(--color-text-secondary)] mt-1">Git history intelligence & churn metrics</p>
        </div>
        <Button onClick={() => { setShowAddModal(true); setFormError(null); }} className="whitespace-nowrap">
          <svg className="w-5 h-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
            <path strokeLinecap="square" strokeLinejoin="miter" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
          Add Repository
        </Button>
      </div>

      {/* ── Add Repository Modal ───────────────────────── */}
      {showAddModal && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={() => setShowAddModal(false)}></div>
          <div className="relative bg-[var(--color-surface-raised)] border-4 border-[var(--color-border)] shadow-[12px_12px_0px_#121212] max-w-lg w-full">
            
            <div className="p-6 border-b-4 border-[var(--color-border)] flex items-center justify-between bg-[var(--color-primary)]">
              <h3 className="text-xl font-black uppercase">Analyze a Repository</h3>
              <button onClick={() => setShowAddModal(false)} className="border-2 border-[var(--color-border)] bg-[var(--color-surface-raised)] p-1 hover:shadow-hard hover:-translate-y-0.5 transition-all">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="square" strokeLinejoin="miter" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <form onSubmit={handleAddRepository} className="p-6 space-y-6">
              <div>
                <label className="block text-sm font-black uppercase mb-2">GitHub Repository URL</label>
                <Input
                  type="url"
                  required
                  value={newRepoUrl}
                  onChange={(e) => setNewRepoUrl(e.target.value)}
                  placeholder="https://github.com/facebook/react"
                  disabled={submitting}
                />
              </div>

              <div>
                <label className="block text-sm font-black uppercase mb-2">Branch (Optional)</label>
                {availableBranches.length > 0 ? (
                  <select
                    value={newRepoBranch}
                    onChange={(e) => setNewRepoBranch(e.target.value)}
                    className="w-full p-3 border-2 border-[var(--color-border)] bg-[var(--color-surface)] font-mono text-sm focus:outline-none focus:shadow-hard transition-shadow"
                    disabled={submitting}
                  >
                    <option value="">Default branch</option>
                    {availableBranches.map(branch => (
                      <option key={branch} value={branch}>{branch}</option>
                    ))}
                  </select>
                ) : (
                  <Input
                    type="text"
                    value={newRepoBranch}
                    onChange={(e) => setNewRepoBranch(e.target.value)}
                    placeholder={fetchingBranches ? "Loading branches..." : "main"}
                    disabled={submitting || fetchingBranches}
                  />
                )}
                <p className="mt-2 text-xs font-medium text-[var(--color-text-secondary)]">
                  If this repository is already tracked, it will be wiped and re-mined.
                </p>
              </div>

              {formError && (
                <div className="p-4 bg-[var(--color-warning)] text-white font-bold border-2 border-[var(--color-border)] shadow-[4px_4px_0px_#121212]">
                  {formError}
                </div>
              )}

              <div className="pt-4 border-t-2 border-[var(--color-border)] flex justify-end gap-4">
                <Button type="button" variant="secondary" onClick={() => setShowAddModal(false)} disabled={submitting}>
                  Cancel
                </Button>
                <Button type="submit" disabled={submitting}>
                  {submitting ? "STARTING MINE..." : "MINE REPOSITORY"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Repositories List ──────────────────────────── */}
      {loadingRepos ? (
        <div className="panel border-4 p-12 text-center text-[var(--color-text-secondary)] font-bold uppercase tracking-widest animate-pulse">
          Loading repositories...
        </div>
      ) : repositories.length === 0 ? (
        <div className="panel border-4 p-16 text-center bg-[var(--color-surface)]">
          <div className="w-16 h-16 mx-auto bg-[var(--color-primary)] border-4 border-[var(--color-border)] shadow-hard mb-6 flex items-center justify-center">
            <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
              <path strokeLinecap="square" strokeLinejoin="miter" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </div>
          <h3 className="text-2xl font-black uppercase mb-2">Your engineering story starts here</h3>
          <p className="text-[var(--color-text-secondary)] font-medium mb-8 max-w-md mx-auto">
            No repositories analyzed yet. Add your first GitHub repository to build your intelligence dashboard.
          </p>
          <Button onClick={() => { setShowAddModal(true); setFormError(null); }}>
            ANALYZE YOUR FIRST REPOSITORY
          </Button>
        </div>
      ) : (
        <div className="space-y-6">
          {repositories.map((repo) => (
            <Card key={repo.id} className="border-4 flex flex-col xl:flex-row gap-6 justify-between items-start xl:items-center">
              
              <div className="space-y-3 flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-3">
                  <h3 className="text-xl font-black truncate" title={repo.name || "Unknown Repository"}>
                    {repo.name || "Unknown Repository"}
                  </h3>
                  {repo.default_branch && (
                    <Badge>{repo.default_branch}</Badge>
                  )}
                  <StatusBadge status={repo.status} />
                </div>

                <a
                  href={repo.github_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-mono text-[var(--color-info)] hover:underline truncate"
                >
                  <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="square" strokeLinejoin="miter" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  <span className="truncate">{repo.github_url}</span>
                </a>

                {repo.status === 'mining' && repo.mining_progress !== undefined && (
                  <div className="w-full max-w-md">
                    <div className="flex justify-between text-xs font-black uppercase mb-1">
                      <span>Mining Progress</span>
                      <span>{repo.mining_progress}%</span>
                    </div>
                    <div className="h-3 border-2 border-[var(--color-border)] bg-[var(--color-surface)] w-full">
                      <div className="h-full bg-[var(--color-primary)] transition-all duration-300" style={{ width: `${repo.mining_progress}%` }}></div>
                    </div>
                  </div>
                )}

                {repo.error_message && (
                  <div className="p-3 bg-[var(--color-warning)] text-white font-bold border-2 border-[var(--color-border)] text-xs uppercase shadow-[2px_2px_0px_#121212]">
                    ERROR: {repo.error_message}
                  </div>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-6 shrink-0 pt-4 xl:pt-0 border-t-2 xl:border-t-0 border-[var(--color-border)] w-full xl:w-auto">
                <div className="text-left xl:text-right">
                  <p className="text-[10px] font-black text-[var(--color-text-tertiary)] uppercase tracking-widest">Commits</p>
                  <p className="text-xl font-black">{repo.total_commits ? repo.total_commits.toLocaleString() : "—"}</p>
                </div>
                
                <div className="text-left xl:text-right">
                  <p className="text-[10px] font-black text-[var(--color-text-tertiary)] uppercase tracking-widest">Files</p>
                  <p className="text-xl font-black">{repo.total_files ? repo.total_files.toLocaleString() : "—"}</p>
                </div>

                <div className="flex items-center gap-3 ml-auto xl:ml-4">
                  {repo.status === "ready" && (
                    <>
                      <Link to={`/repository/${repo.id}`}>
                        <Button className="px-4 py-2 text-xs">ANALYTICS</Button>
                      </Link>
                      <Link to={`/repository/${repo.id}/architecture`}>
                        <Button variant="secondary" className="px-4 py-2 text-xs">ARCHITECTURE</Button>
                      </Link>
                    </>
                  )}
                  
                  <button onClick={() => handleRetryRepository(repo)} className="p-2 border-2 border-[var(--color-border)] bg-[var(--color-surface-raised)] hover:bg-[var(--color-primary)] shadow-[2px_2px_0px_#121212] transition-colors" title="Retry / Re-mine">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="square" strokeLinejoin="miter" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  </button>
                  <button onClick={() => handleDeleteRepository(repo.id, repo.name)} className="p-2 border-2 border-[var(--color-border)] bg-[var(--color-surface-raised)] hover:bg-[var(--color-warning)] hover:text-white shadow-[2px_2px_0px_#121212] transition-colors" title="Delete">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="square" strokeLinejoin="miter" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
