import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';
import { Loader2, X, FileCode, Users, GitCommit, Target } from 'lucide-react';

export default function NodeInspector({ repoId, node, onClose }) {
  const [loading, setLoading] = useState(true);
  const [moduleStats, setModuleStats] = useState(null);

  useEffect(() => {
    let isMounted = true;
    
    async function loadNodeIntelligence() {
      if (!node || node.type !== 'module') {
        setLoading(false);
        return;
      }
      
      setLoading(true);
      try {
        // Reuse the existing hotspots analytics endpoint to derive module-level intelligence
        const hotspots = await api.get(`/api/analytics/${repoId}/hotspots`);
        
        if (!isMounted) return;

        // Filter files that belong to this module (based on node label/directory)
        const moduleFiles = hotspots.filter(h => {
           if (node.label === "root") return !h.file_path.includes("/");
           return h.file_path.startsWith(node.label + "/");
        });

        const totalCommits = moduleFiles.reduce((acc, f) => acc + f.commits_count, 0);
        const authors = new Set();
        moduleFiles.forEach(f => {
          f.authors.forEach(a => authors.add(a));
        });

        // Determine top author based on sum of commits where they were top
        const authorCounts = {};
        moduleFiles.forEach(f => {
           if (f.top_author) {
             authorCounts[f.top_author] = (authorCounts[f.top_author] || 0) + f.commits_count;
           }
        });
        const topAuthor = Object.entries(authorCounts)
           .sort((a, b) => b[1] - a[1])[0]?.[0] || 'Unknown';

        setModuleStats({
          fileCount: moduleFiles.length,
          totalCommits,
          authorCount: authors.size,
          topAuthor,
        });

      } catch (err) {
        console.error("Failed to load node intelligence:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    loadNodeIntelligence();

    return () => {
      isMounted = false;
    };
  }, [repoId, node]);

  return (
    <div className="w-80 border-l border-slate-200 bg-white h-full shadow-xl flex flex-col z-20">
      <div className="px-4 py-3 border-b border-slate-200 flex justify-between items-center bg-slate-50">
        <h3 className="font-semibold text-slate-800 flex items-center gap-2">
          <Target className="w-4 h-4 text-indigo-600" />
          Node Inspector
        </h3>
        <button onClick={onClose} className="p-1 hover:bg-slate-200 rounded-full text-slate-500">
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="p-4 flex-1 overflow-y-auto">
        <div className="mb-6">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">ID</p>
          <p className="text-sm font-mono bg-slate-100 p-2 rounded text-slate-700 break-all">{node.id}</p>
        </div>

        <div className="mb-6">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Label</p>
          <p className="text-lg font-bold text-slate-800">{node.label}</p>
        </div>
        
        <div className="mb-6">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Type</p>
          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize
            ${node.type === 'module' ? 'bg-indigo-100 text-indigo-800' : 'bg-emerald-100 text-emerald-800'}
          `}>
            {node.type}
          </span>
          {node.category && (
            <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-800 capitalize">
              {node.category}
            </span>
          )}
        </div>

        {node.type === 'module' && (
          <div className="pt-4 border-t border-slate-200">
            <h4 className="text-sm font-semibold text-slate-800 mb-4">Module Intelligence</h4>
            
            {loading ? (
              <div className="flex justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-indigo-500" />
              </div>
            ) : moduleStats ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-1 text-slate-500 mb-1">
                    <FileCode className="w-3.5 h-3.5" />
                    <span className="text-xs font-medium">Files</span>
                  </div>
                  <p className="text-lg font-bold text-slate-700">{moduleStats.fileCount}</p>
                </div>
                
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-1 text-slate-500 mb-1">
                    <GitCommit className="w-3.5 h-3.5" />
                    <span className="text-xs font-medium">Commits</span>
                  </div>
                  <p className="text-lg font-bold text-slate-700">{moduleStats.totalCommits}</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-1 text-slate-500 mb-1">
                    <Users className="w-3.5 h-3.5" />
                    <span className="text-xs font-medium">Authors</span>
                  </div>
                  <p className="text-lg font-bold text-slate-700">{moduleStats.authorCount}</p>
                </div>

                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <div className="flex items-center gap-1 text-slate-500 mb-1">
                    <span className="text-xs font-medium">Top Author</span>
                  </div>
                  <p className="text-sm font-bold text-slate-700 truncate" title={moduleStats.topAuthor}>
                    {moduleStats.topAuthor}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-sm text-slate-500">No telemetry available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
