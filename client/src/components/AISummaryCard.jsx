import React, { useState } from 'react';
import { api } from '../lib/api';

export default function AISummaryCard({ repoId }) {
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'success' | 'error'
  const [summaryData, setSummaryData] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isStale, setIsStale] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');

  const fetchSummary = async (force = false) => {
    if (status === 'loading') return;
    setStatus('loading');
    setErrorMsg('');
    try {
      const data = await api.getAISummary(repoId, { model: selectedModel, force_refresh: force });
      if (data && data.summary) {
        setSummaryData(data.summary);
        setIsStale(data.is_stale || false);
        setStatus('success');
      } else {
        // Handle case where backend returned empty (e.g. not cached and force=false, or generation failed silently)
        setStatus('idle');
      }
    } catch (err) {
      setErrorMsg(err.message || 'AI generation unavailable. Please try again.');
      setStatus('error');
    }
  };

  const techStack = summaryData?.technology_stack || {};
  const hasTech = (techStack.languages?.length > 0) || 
                  (techStack.frameworks?.length > 0) || 
                  (techStack.databases?.length > 0) || 
                  (techStack.infrastructure?.length > 0);

  return (
    <div className="card flex flex-col max-h-[800px]">
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6 shrink-0">
        <h3 className="text-xl font-bold text-text-primary flex items-center gap-2">
          <span className="w-3 h-3 bg-special shadow-hard-sm"></span>
          AI Summary
        </h3>
        {status === 'success' && (
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
            <button
              onClick={() => fetchSummary(true)}
              disabled={status === 'loading'}
              className="btn btn-secondary text-xs px-3 py-1.5"
            >
              {isStale ? "Generate Updated" : "Regenerate"}
            </button>
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto pr-2">
        {status === 'error' && (
          <div className="mb-4 panel border-warning border-l-4">
            <p className="font-bold text-warning mb-2">Failed to load AI Summary</p>
            <p className="text-sm text-text-secondary mb-4">{errorMsg}</p>
            <button onClick={() => fetchSummary(true)} className="btn btn-secondary text-xs">
              Retry
            </button>
          </div>
        )}
        
        {status === 'loading' && (
          <div className="space-y-4 animate-pulse-soft py-4">
            <div className="h-4 bg-border-subtle w-3/4"></div>
            <div className="h-4 bg-border-subtle w-full"></div>
            <div className="h-4 bg-border-subtle w-5/6"></div>
            <div className="h-4 bg-border-subtle w-1/2"></div>
            <div className="text-xs font-bold text-text-tertiary mt-4">ANALYZING REPOSITORY...</div>
          </div>
        )}

        {status === 'success' && summaryData && (
          <div className="flex flex-col gap-6">
            {isStale && (
              <div className="panel border-warning bg-surface-raised flex items-center justify-between">
                <span className="text-sm font-bold text-warning">Analysis is outdated (new commits found)</span>
                <button
                  onClick={() => fetchSummary(true)}
                  disabled={status === 'loading'}
                  className="btn btn-secondary text-xs px-2 py-1"
                >
                  Update
                </button>
              </div>
            )}
            
            {/* Repository Identity */}
            {(summaryData.what_is_this || summaryData.architecture_overview) && (
              <section className="space-y-3">
                <h4 className="text-xs font-bold text-text-tertiary uppercase tracking-widest border-b-2 border-border pb-1">Repository</h4>
                {summaryData.what_is_this && (
                  <p className="text-sm text-text-primary leading-relaxed font-medium">
                    {summaryData.what_is_this}
                  </p>
                )}
                {summaryData.architecture_overview && (
                  <p className="text-sm text-text-secondary leading-relaxed">
                    {summaryData.architecture_overview}
                  </p>
                )}
              </section>
            )}

            {/* Technology Stack */}
            {hasTech && (
              <section className="space-y-3">
                <h4 className="text-xs font-bold text-text-tertiary uppercase tracking-widest border-b-2 border-border pb-1">Technology Stack</h4>
                {techStack && Object.keys(techStack).length > 0 && (
                  <div className="flex flex-col gap-3">
                    {Object.entries(techStack).map(([category, items]) => {
                      if (!Array.isArray(items) || items.length === 0) return null;
                      return (
                        <div key={category}>
                          <span className="text-[10px] font-bold text-text-secondary uppercase mb-1 block">
                            {category.replace(/_/g, ' ')}
                          </span>
                          <div className="flex flex-wrap gap-2">
                            {items.map(t => (
                              <span key={t} className="badge badge-primary">{t}</span>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </section>
            )}
            {/* Hotspots */}
            {summaryData.key_areas && summaryData.key_areas.length > 0 && (
              <section className="space-y-3">
                <h4 className="text-xs font-bold text-text-tertiary uppercase tracking-widest border-b-2 border-border pb-1">Hotspots</h4>
                <div className="flex flex-col gap-3">
                  {summaryData.key_areas.map((area, idx) => (
                    <div key={idx} className="panel bg-surface p-3 border-l-4 border-l-warning">
                      <div className="text-technical font-bold text-text-primary mb-1 break-all">
                        {area.area}
                      </div>
                      <div className="text-xs text-text-secondary">
                        {area.why_important}
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Onboarding Notes */}
            {summaryData.onboarding_notes && (
              <section className="space-y-3">
                <h4 className="text-xs font-bold text-text-tertiary uppercase tracking-widest border-b-2 border-border pb-1">Onboarding</h4>
                <div className="panel bg-surface border-special">
                  <p className="text-sm text-text-primary leading-relaxed font-medium">
                    {summaryData.onboarding_notes}
                  </p>
                </div>
              </section>
            )}
            
          </div>
        )}

        {status === 'idle' && (
          <div className="flex flex-col items-center justify-center py-10 gap-4 text-center px-4 panel border-dashed">
            <div className="w-12 h-12 bg-surface-raised border-2 border-border flex items-center justify-center mb-2 shadow-hard-sm">
               <span className="font-bold text-special text-xl">?</span>
            </div>
            <div className="text-sm font-bold text-text-primary">
              No analysis generated yet.
            </div>
            <p className="text-xs text-text-secondary max-w-xs mb-2">
              Analyze this codebase with AI to understand its architecture and stack.
            </p>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xs text-text-tertiary">Model:</span>
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="text-xs border border-divider bg-surface rounded-md text-text-secondary cursor-pointer py-1.5 pl-3 pr-8"
              >
                <option value="auto">Auto (Recommended)</option>
                <option value="gemini_flash">Gemini Flash</option>
                <option value="gemini_flash_lite">Gemini Flash Lite</option>
                <option value="groq">Groq Llama 3</option>
              </select>
            </div>
            <button
              onClick={() => fetchSummary(true)}
              className="btn btn-primary"
            >
              Generate Summary
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
