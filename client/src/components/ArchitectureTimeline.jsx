import React, { useState } from 'react';
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
  const [selectedModel, setSelectedModel] = useState('auto');

  const fetchShifts = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAIShifts(repoId, { model: selectedModel });
      setShifts(data.shifts || []);
      setGenerated(true);
    } catch (err) {
      setError(err.message || 'Failed to detect architecture shifts.');
    } finally {
      setLoading(false);
    }
  };

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
            <button
              onClick={fetchShifts}
              disabled={loading}
              title="Regenerate"
              className="p-1.5 rounded-md text-text-tertiary hover:text-text-primary hover:bg-surface-hover transition-colors disabled:opacity-40"
            >
              <svg className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        )}
      </div>

      <div className="px-6 pb-6 pt-2 overflow-y-auto [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:bg-border [&::-webkit-scrollbar-thumb]:rounded-full hover:[&::-webkit-scrollbar-thumb]:bg-text-tertiary [&::-webkit-scrollbar-track]:bg-transparent">
        {loading ? (
          <div className="space-y-4 animate-pulse">
            <div className="h-12 bg-surface-hover rounded w-full"></div>
            <div className="h-12 bg-surface-hover rounded w-5/6"></div>
            <div className="h-12 bg-surface-hover rounded w-4/5"></div>
          </div>
        ) : error ? (
          <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm flex gap-3 items-start">
            <svg className="w-5 h-5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>{error}</span>
          </div>
        ) : shifts.length > 0 ? (
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
            <button
              onClick={fetchShifts}
              disabled={loading}
              className="group flex items-center gap-2 px-5 py-2.5 bg-surface-hover border border-divider rounded-xl hover:border-indigo-300 hover:bg-indigo-50 transition-all disabled:opacity-50"
            >
              <svg className="w-5 h-5 text-text-tertiary group-hover:text-indigo-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 00-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 001.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 001.423 1.423l1.183.394-1.183.394a2.25 2.25 0 00-1.423 1.423z" />
              </svg>
              <span className="text-sm font-medium text-text-secondary group-hover:text-indigo-600 transition-colors">
                Detect Architecture Shifts
              </span>
            </button>
            <p className="text-xs text-text-tertiary">Analyze commit history for major structural changes</p>
          </div>
        )}
      </div>
    </div>
  );
}
