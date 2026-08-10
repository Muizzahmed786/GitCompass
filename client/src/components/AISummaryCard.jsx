import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function AISummaryCard({ repoId }) {
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    // Optionally auto-fetch if we want, or rely on a button. Let's auto-fetch for seamless UX.
    fetchSummary();
  }, [repoId]);

  const fetchSummary = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAISummary(repoId);
      setSummary(data.summary);
    } catch (err) {
      setError(err.message || 'Failed to generate AI summary.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-divider p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
          <svg className="w-5 h-5 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          </svg>
          AI Evolution Summary
        </h3>
        <button 
          onClick={fetchSummary}
          disabled={loading}
          className="text-sm px-3 py-1 bg-primary-50 text-primary-600 rounded-md hover:bg-primary-100 transition-colors disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Refresh'}
        </button>
      </div>

      {loading && !summary ? (
        <div className="space-y-3 animate-pulse">
          <div className="h-4 bg-surface-hover rounded w-3/4"></div>
          <div className="h-4 bg-surface-hover rounded w-full"></div>
          <div className="h-4 bg-surface-hover rounded w-5/6"></div>
        </div>
      ) : error ? (
        <div className="text-red-500 text-sm">{error}</div>
      ) : summary ? (
        <div className="prose prose-sm text-text-secondary whitespace-pre-wrap">
          {summary}
        </div>
      ) : (
        <div className="text-text-secondary text-sm">No summary available.</div>
      )}
    </div>
  );
}
