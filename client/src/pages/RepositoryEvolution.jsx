import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import AIDevelopmentStory from "../components/AIDevelopmentStory";

export default function RepositoryEvolution() {
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
    return <div className="card p-12 text-center text-text-secondary animate-pulse-soft">Loading evolution...</div>;
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
        <h1 className="text-2xl font-bold text-text-primary tracking-tight">
          {repo.name || repo.github_url} — Evolution
        </h1>
        <p className="mt-1 text-sm text-text-secondary">
          Full Development Story and Milestones
        </p>
      </div>
      
      <div className="grid grid-cols-1">
        <AIDevelopmentStory repoId={id} />
      </div>
    </div>
  );
}
