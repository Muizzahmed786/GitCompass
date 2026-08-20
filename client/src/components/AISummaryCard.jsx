import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../lib/api';

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      title="Copy to clipboard"
      className="p-1.5 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors"
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
  );
}

export default function AISummaryCard({ repoId }) {
  const [summary, setSummary] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generated, setGenerated] = useState(false);
  const [isStale, setIsStale] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');

  const fetchSummary = async (force = false) => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAISummary(repoId, { model: selectedModel, force_refresh: force });
      setSummary(data.summary || '');
      setIsStale(data.is_stale || false);
      setGenerated(!!data.summary);
    } catch (err) {
      setError(err.message || 'Failed to generate AI summary.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSummary(false);
  }, [repoId, selectedModel]);

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-divider flex flex-col max-h-[500px]">
      <div className="flex justify-between items-center px-6 pt-6 pb-4 shrink-0 border-b border-transparent">
        <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
          <svg className="w-5 h-5 text-primary-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
          </svg>
          AI Evolution Summary
        </h3>
        {(generated || !!error) && (
          <div className="flex items-center gap-2">
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="text-xs border-none bg-surface-hover rounded-md text-text-secondary focus:ring-0 cursor-pointer py-1 pl-2 pr-6"
            >
              <option value="auto">Auto</option>
              <option value="gemini_flash">Gemini Flash</option>
              <option value="gemini_flash_lite">Flash Lite</option>
              <option value="groq">Groq</option>
            </select>
            {summary && <CopyButton text={summary} />}
            {summary && (
              <button
                onClick={() => fetchSummary(true)}
                disabled={loading}
                title={isStale ? "Generate Updated Analysis" : "Regenerate Analysis"}
                className="px-2 py-1 text-xs rounded-md bg-surface-hover border border-divider hover:bg-primary-50 hover:text-primary-600 transition-colors disabled:opacity-50"
              >
                {isStale ? "Generate Updated" : "Regenerate"}
              </button>
            )}
          </div>
        )}
      </div>

      <div className="px-6 pb-6 pt-2 overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-text-tertiary [&::-webkit-scrollbar-track]:bg-transparent">
        {error && (
          <div className="mb-4 text-red-500 text-sm bg-red-50 rounded-lg p-3">{error}</div>
        )}
        
        {loading && !summary ? (
          <div className="space-y-3 animate-pulse">
            <div className="h-4 bg-surface-hover rounded w-3/4"></div>
            <div className="h-4 bg-surface-hover rounded w-full"></div>
            <div className="h-4 bg-surface-hover rounded w-5/6"></div>
            <div className="h-4 bg-surface-hover rounded w-full"></div>
            <div className="h-4 bg-surface-hover rounded w-2/3"></div>
          </div>
        ) : summary ? (
          <div className="flex flex-col">
            {isStale && (
              <div className="mb-4 p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-between">
                <span className="text-sm text-amber-800">Analysis is outdated. The repository has new commits.</span>
                <button
                  onClick={() => fetchSummary(true)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-semibold bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50 transition-colors"
                >
                  Generate Updated Analysis
                </button>
              </div>
            )}
            <div className="prose prose-sm max-w-none text-text-secondary [&>p]:mb-3 [&>p:last-child]:mb-0 [&>ul]:mb-3 [&>ul]:pl-4 [&_li]:mb-1 [&_strong]:text-text-primary [&_code]:bg-surface-hover [&_code]:px-1 [&_code]:rounded [&_code]:text-xs [&_h1]:text-base [&_h1]:font-bold [&_h1]:text-text-primary [&_h2]:text-sm [&_h2]:font-bold [&_h2]:text-text-primary [&_h3]:text-sm [&_h3]:font-semibold [&_h3]:text-text-primary">
              <ReactMarkdown>{summary}</ReactMarkdown>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 gap-3">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-text-tertiary">Model:</span>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="text-xs border border-divider bg-surface rounded-md text-text-secondary focus:ring-primary-500 cursor-pointer py-1.5 pl-3 pr-8"
              >
                <option value="auto">Auto (Recommended)</option>
                <option value="gemini_flash">Gemini Flash</option>
                <option value="gemini_flash_lite">Gemini Flash Lite</option>
                <option value="groq">Groq Llama 3</option>
              </select>
            </div>
            <div className="text-sm text-text-secondary mb-4 text-center">
              No analysis has been generated for this repository yet.
            </div>
            <button
              onClick={() => fetchSummary(true)}
              disabled={loading}
              className="group flex items-center gap-2 px-5 py-2.5 bg-surface-hover border border-divider rounded-xl hover:border-primary-300 hover:bg-primary-50 transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5 text-text-tertiary group-hover:text-primary-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
              </svg>
              <span className="text-sm font-medium text-text-secondary group-hover:text-primary-600 transition-colors">
                Generate Analysis
              </span>
            </button>
            <p className="text-xs text-text-tertiary">Analyze this codebase with AI</p>
          </div>
        )}
      </div>
    </div>
  );
}
