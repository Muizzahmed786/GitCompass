import React, { useState } from 'react';
import { api } from '../lib/api';

export default function ArchitectureTimeline({ repoId }) {
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'success' | 'error'
  const [shifts, setShifts] = useState([]);
  const [errorMsg, setErrorMsg] = useState('');
  const [isStale, setIsStale] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');

  const fetchShifts = async (force = false) => {
    if (status === 'loading') return;
    setStatus('loading');
    setErrorMsg('');
    try {
      const data = await api.getAIShifts(repoId, { model: selectedModel, force_refresh: force });
      
      let parsedShifts = [];
      if (data && data.shifts) {
        // Backend could return `{"shifts": [...]}` or just `[...]` depending on LLM parsing
        // If data.shifts is already an array, use it directly.
        // If the LLM hallucinated and nested it like {"shifts": {"shifts": [...]}}, try to unwrap.
        if (Array.isArray(data.shifts)) {
          parsedShifts = data.shifts;
        } else if (data.shifts && Array.isArray(data.shifts.shifts)) {
          parsedShifts = data.shifts.shifts;
        } else if (typeof data.shifts === 'string') {
           try { parsedShifts = JSON.parse(data.shifts); } catch(e) {}
        }
        setShifts(parsedShifts);
        setIsStale(data.is_stale || false);
        setStatus('success');
      } else {
        setStatus('idle');
      }
    } catch (err) {
      setErrorMsg(err.message || 'AI generation unavailable. Please try again.');
      setStatus('error');
    }
  };

  return (
    <div className="card flex flex-col max-h-[800px]">
      <div className="flex flex-wrap justify-between items-start gap-4 mb-6 shrink-0">
        <h3 className="text-xl font-bold text-text-primary flex items-center gap-2">
          <span className="w-3 h-3 bg-info shadow-hard-sm"></span>
          Architecture Shifts
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
              onClick={() => fetchShifts(true)}
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
            <p className="font-bold text-warning mb-2">Failed to load Timeline</p>
            <p className="text-sm text-text-secondary mb-4">{errorMsg}</p>
            <button onClick={() => fetchShifts(true)} className="btn btn-secondary text-xs">
              Retry
            </button>
          </div>
        )}
        
        {status === 'loading' && (
          <div className="space-y-6 animate-pulse-soft py-4">
            <div className="h-24 bg-surface-raised border-2 border-border shadow-hard-sm w-full"></div>
            <div className="h-24 bg-surface-raised border-2 border-border shadow-hard-sm w-5/6 ml-auto"></div>
            <div className="text-xs font-bold text-text-tertiary mt-4 text-center">ANALYZING ARCHITECTURE...</div>
          </div>
        )}

        {status === 'success' && shifts && (
          <div className="flex flex-col gap-6 relative">
            {isStale && (
              <div className="panel border-warning bg-surface-raised flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-warning">Analysis is outdated (new commits found)</span>
                <button
                  onClick={() => fetchShifts(true)}
                  disabled={status === 'loading'}
                  className="btn btn-secondary text-xs px-2 py-1"
                >
                  Update
                </button>
              </div>
            )}
            
            {shifts.length === 0 ? (
              <div className="text-center py-10">
                <p className="text-sm font-bold text-text-tertiary">No major architectural shifts detected.</p>
              </div>
            ) : (
              <div className="relative border-l-[3px] border-border ml-4 space-y-8 pb-4">
                {shifts.map((shift, idx) => (
                  <div key={idx} className="pl-6 relative">
                    <div className="absolute w-4 h-4 bg-info border-2 border-border -left-[10px] top-1"></div>
                    <div className="mb-1">
                      <span className="badge badge-info bg-surface text-info border-info">{shift.date}</span>
                    </div>
                    <h4 className="text-base font-bold text-text-primary mb-3">{shift.title}</h4>
                    
                    <div className="flex flex-col gap-4">
                      {/* Evidence Block */}
                      {(shift.what_changed || (shift.evidence_items && shift.evidence_items.length > 0)) && (
                        <div className="panel bg-surface-hover/50 p-4 border-l-4 border-l-border border-t-0 border-r-0 border-b-0 shadow-none">
                          <h5 className="text-[10px] font-bold text-text-secondary uppercase mb-2 tracking-wider">Evidence</h5>
                          {shift.what_changed && (
                            <p className="text-sm text-text-primary mb-3">
                              {shift.what_changed}
                            </p>
                          )}
                          {shift.evidence_items && shift.evidence_items.length > 0 && (
                            <ul className="text-xs text-technical text-text-secondary space-y-1">
                              {shift.evidence_items.map((item, i) => (
                                <li key={i} className="flex gap-2">
                                  <span className="text-border-subtle shrink-0">→</span>
                                  <span>{item}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      )}
                      
                      {/* Inference Block */}
                      {shift.architectural_significance && (
                        <div className="panel bg-surface-raised border-info border-l-4">
                          <h5 className="text-[10px] font-bold text-info uppercase mb-2 tracking-wider">[INFERENCE] Significance</h5>
                          <p className="text-sm text-text-primary leading-relaxed font-medium">
                            {shift.architectural_significance}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {status === 'idle' && (
          <div className="flex flex-col items-center justify-center py-10 gap-4 text-center px-4 panel border-dashed">
            <div className="w-12 h-12 bg-surface-raised border-2 border-border flex items-center justify-center mb-2 shadow-hard-sm">
               <span className="font-bold text-info text-xl">#</span>
            </div>
            <div className="text-sm font-bold text-text-primary">
              No timeline generated yet.
            </div>
            <p className="text-xs text-text-secondary max-w-xs mb-2">
              Analyze commit history to discover major structural shifts and migrations over time.
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
              onClick={() => fetchShifts(true)}
              className="btn btn-primary"
            >
              Analyze Architecture
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
