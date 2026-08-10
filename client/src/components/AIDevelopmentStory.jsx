import React, { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../lib/api';

export default function AIDevelopmentStory({ repoId }) {
  const [story, setStory] = useState(null);
  const [loading, setLoading] = useState(false); // Default to false
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const fetchStory = useCallback(async () => {
    if (loading) return; // Prevent concurrent requests
    
    setLoading(true);
    setError(null);
    try {
      const data = await api.post(`/api/ai/story/${repoId}`);
      setStory(data.story);
    } catch (err) {
      setError(err.message || "Failed to generate development story");
    } finally {
      setLoading(false);
    }
  }, [repoId, loading]);

  // Removed useEffect auto-fetch completely to prevent API calls on mount, re-renders, or polling.

  const handleCopy = async () => {
    if (!story) return;
    await navigator.clipboard.writeText(story);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-divider p-6 h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h3 className="font-bold text-text-primary text-base">Development Story</h3>
            <p className="text-xs text-text-tertiary">Chronological narrative of how the repository evolved over time</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {story && !loading && (
            <>
              <button
                onClick={handleCopy}
                title="Copy Story"
                className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors"
              >
                {copied ? (
                  <svg className="w-4 h-4 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                ) : (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                )}
              </button>
              <button
                onClick={fetchStory}
                disabled={loading}
                title="Regenerate Story"
                className="p-1.5 rounded-lg text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-50"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col justify-center">
        {loading ? (
          <div className="space-y-3 animate-pulse py-4">
            <div className="h-4 bg-surface-hover rounded w-3/4"></div>
            <div className="h-4 bg-surface-hover rounded w-full"></div>
            <div className="h-4 bg-surface-hover rounded w-5/6"></div>
            <div className="h-4 bg-surface-hover rounded w-2/3"></div>
            <div className="text-center text-xs text-text-tertiary mt-4">Generating narrative...</div>
          </div>
        ) : error ? (
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm flex items-center justify-between">
            <span>{error}</span>
            <button
              onClick={fetchStory}
              disabled={loading}
              className="px-3 py-1.5 text-xs font-semibold bg-rose-600 text-white rounded hover:bg-rose-700 disabled:opacity-50 transition-colors"
            >
              Try Again
            </button>
          </div>
        ) : story ? (
          <div className="prose prose-sm max-w-none text-text-secondary leading-relaxed bg-surface-hover/20 p-4 rounded-xl border border-divider/50 [&>p]:mb-3 [&>p:last-child]:mb-0 [&_strong]:text-indigo-600 [&_strong]:font-semibold">
            <ReactMarkdown>{story}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-10 text-center px-4 bg-surface-hover/20 rounded-xl border border-dashed border-divider">
            <div className="w-12 h-12 bg-indigo-50 rounded-full flex items-center justify-center mb-4">
              <svg className="w-6 h-6 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <h4 className="text-text-primary font-medium mb-2">Generate Story</h4>
            <p className="text-sm text-text-tertiary mb-6 max-w-sm">
              Use AI to summarize the repository's commit history into a readable, chronological development story.
            </p>
            <button
              onClick={fetchStory}
              disabled={loading}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-lg bg-indigo-600 text-white text-sm font-medium hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Generate Development Story
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
