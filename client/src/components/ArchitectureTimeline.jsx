import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import { api } from '../lib/api';

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    const plainText = text.map(s => `[${s.date}] ${s.title}\n${s.description}`).join('\n\n');
    await navigator.clipboard.writeText(plainText);
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

export default function ArchitectureTimeline({ repoId }) {
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generated, setGenerated] = useState(false);
  const [isStale, setIsStale] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');

  const fetchShifts = async (force = false) => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAIShifts(repoId, { model: selectedModel, force_refresh: force });
      setShifts(data.shifts || []);
      setIsStale(data.is_stale || false);
      setGenerated(!!data.shifts);
    } catch (err) {
      setError(err.message || 'Failed to detect architecture shifts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchShifts(false);
  }, [repoId, selectedModel]);

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-divider flex flex-col max-h-[500px]">
      <div className="flex justify-between items-center px-6 pt-6 pb-4 shrink-0 border-b border-transparent">
        <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Architecture Shift Timeline
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
            {shifts.length > 0 && <CopyButton text={shifts} />}
            {shifts.length > 0 && (
              <button
                onClick={() => fetchShifts(true)}
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
          <div className="mb-4 bg-red-50 text-red-600 p-4 rounded-lg text-sm flex gap-3 items-start">
            <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        )}
        
        {loading && shifts.length === 0 ? (
          <div className="space-y-4 animate-pulse">
            <div className="h-12 bg-surface-hover rounded w-full"></div>
            <div className="h-12 bg-surface-hover rounded w-5/6"></div>
            <div className="h-12 bg-surface-hover rounded w-4/5"></div>
          </div>
        ) : shifts.length > 0 ? (
          <div className="flex flex-col">
            {isStale && (
              <div className="mb-4 mx-3 p-3 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-between">
                <span className="text-sm text-amber-800">Analysis is outdated. The repository has new commits.</span>
                <button
                  onClick={() => fetchShifts(true)}
                  disabled={loading}
                  className="px-3 py-1.5 text-xs font-semibold bg-amber-600 text-white rounded hover:bg-amber-700 disabled:opacity-50 transition-colors"
                >
                  Generate Updated Analysis
                </button>
              </div>
            )}
            <div className="relative border-l-2 border-divider ml-3 space-y-6">
              {shifts.map((shift, index) => (
                <div key={index} className="pl-6 relative">
                  <div className="absolute w-3 h-3 bg-indigo-500 rounded-full -left-[7px] top-1.5 ring-4 ring-surface"></div>
                  <div className="text-xs font-semibold text-indigo-500 mb-1">{shift.date}</div>
                  <div className="font-bold text-text-primary mb-1">{shift.title}</div>
                  <div className="text-sm text-text-secondary prose prose-sm max-w-none [&>p]:m-0 [&_strong]:text-text-primary [&_code]:bg-surface-hover [&_code]:px-1 [&_code]:rounded [&_code]:text-xs">
                    <ReactMarkdown>{shift.description}</ReactMarkdown>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : generated ? (
          <div className="text-center py-6 text-text-tertiary text-sm">
            No clear architectural shifts found in the commit history.
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
              onClick={() => fetchShifts(true)}
              disabled={loading}
              className="group flex items-center gap-2 px-5 py-2.5 bg-surface-hover border border-divider rounded-xl hover:border-primary-300 hover:bg-primary-50 transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5 text-text-tertiary group-hover:text-primary-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
              <span className="text-sm font-medium text-text-secondary group-hover:text-primary-600 transition-colors">
                Generate Analysis
              </span>
            </button>
            <p className="text-xs text-text-tertiary">Analyze commit history for major structural changes</p>
          </div>
        )}
      </div>
    </div>
  );
}
