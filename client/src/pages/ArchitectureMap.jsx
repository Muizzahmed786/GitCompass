import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../lib/api";
import { ArrowLeft, RefreshCw, GitFork, LayoutTemplate } from "lucide-react";
import ArchitectureGraph from "../components/ArchitectureGraph";

export default function ArchitectureMap() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [graphData, setGraphData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const repoData = await api.get(`/api/repositories/${id}`);
      setRepo(repoData);

      const graph = await api.get(`/api/analytics/${id}/knowledge-graph`);
      setGraphData(graph);
    } catch (err) {
      setError(err.message || "Failed to load architecture graph data");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  if (loading) {
    return (
      <div className="flex flex-col h-[calc(100vh-8rem)] items-center justify-center space-y-4">
        <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin" />
        <p className="text-slate-500 font-medium animate-pulse">
          Analyzing Repository Architecture...
        </p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6 mt-8 bg-red-50 text-red-600 rounded-xl border border-red-100 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold">Failed to load graph</h2>
          <p className="text-sm opacity-90">{error}</p>
        </div>
        <button
          onClick={loadData}
          className="px-4 py-2 bg-red-100 hover:bg-red-200 rounded-lg text-sm font-semibold transition-colors"
        >
          Try Again
        </button>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-5rem)] flex flex-col pt-4">
      <div className="px-6 mb-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link
            to={`/repositories/${id}`}
            className="p-2 hover:bg-slate-200 rounded-full transition-colors group"
          >
            <ArrowLeft className="w-5 h-5 text-slate-500 group-hover:text-slate-800" />
          </Link>
          <div>
            <div className="flex items-center gap-2 mb-0.5">
              <h1 className="text-2xl font-bold text-slate-800 tracking-tight">
                Architecture Map
              </h1>
              <span className="bg-indigo-100 text-indigo-700 text-xs px-2.5 py-1 rounded-full font-bold uppercase tracking-widest flex items-center gap-1">
                <LayoutTemplate className="w-3 h-3" />
                Phase 9
              </span>
            </div>
            <p className="text-slate-500 text-sm flex items-center gap-1.5">
              <GitFork className="w-4 h-4 text-slate-400" />
              {repo?.name || "Loading..."}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="p-2 hover:bg-slate-200 text-slate-500 rounded-full transition-colors flex items-center justify-center group"
            title="Reload Map"
          >
            <RefreshCw className="w-5 h-5 group-hover:rotate-180 transition-transform duration-500" />
          </button>
        </div>
      </div>

      <div className="flex-1 w-full px-6 pb-6 overflow-hidden">
        <ArchitectureGraph repoId={id} graphData={graphData} />
      </div>
    </div>
  );
}
