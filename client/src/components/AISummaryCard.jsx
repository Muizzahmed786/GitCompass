import React, { useState } from 'react';
import { api } from '../lib/api';

export default function AISummaryCard({ repoId }) {
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generated, setGenerated] = useState(false);

  const fetchSummary = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAISummary(repoId);
      setSummary(data.summary);
      setGenerated(true);
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
          {/* Sparkle outline icon */}
          <svg className="w-5 h-5 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
          </svg>
          AI Evolution Summary
        </h3>
        {generated && (
          <button
            onClick={fetchSummary}
            disabled={loading}
            className="text-sm px-3 py-1 bg-primary-50 text-primary-600 rounded-md hover:bg-primary-100 transition-colors disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Refresh'}
          </button>
        )}
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
        <div className="flex flex-col items-center justify-center py-8 gap-3">
          <button
            onClick={fetchSummary}
            disabled={loading}
            className="group flex items-center gap-2 px-5 py-2.5 bg-surface-hover border border-divider rounded-xl hover:border-primary-300 hover:bg-primary-50 transition-all disabled:opacity-50"
          >
            {/* Sparkle outline icon (larger, interactive) */}
            <svg className="w-5 h-5 text-text-tertiary group-hover:text-primary-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
            </svg>
            <span className="text-sm font-medium text-text-secondary group-hover:text-primary-600 transition-colors">
              Generate AI Summary
            </span>
          </button>
          <p className="text-xs text-text-tertiary">Click to analyze the codebase with Gemini AI</p>
        </div>
      )}
    </div>
  );
}
