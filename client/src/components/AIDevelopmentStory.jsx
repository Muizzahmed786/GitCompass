import React, { useState } from 'react';
import { api } from '../lib/api';

export default function AIDevelopmentStory({ repoId }) {
  const [status, setStatus] = useState('idle'); // 'idle' | 'loading' | 'success' | 'error'
  const [story, setStory] = useState(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [isStale, setIsStale] = useState(false);
  const [selectedModel, setSelectedModel] = useState('auto');

  const fetchStory = async (force = false) => {
    if (status === 'loading') return;
    setStatus('loading');
    setErrorMsg('');
    try {
      const data = await api.getAIStory(repoId, { model: selectedModel, force_refresh: force });
      if (data && data.story) {
        setStory(data.story);
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
          <span className="w-3 h-3 bg-primary shadow-hard-sm"></span>
          Development Story
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
              onClick={() => fetchStory(true)}
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
            <p className="font-bold text-warning mb-2">Failed to load Development Story</p>
            <p className="text-sm text-text-secondary mb-4">{errorMsg}</p>
            <button onClick={() => fetchStory(true)} className="btn btn-secondary text-xs">
              Retry
            </button>
          </div>
        )}
        
        {status === 'loading' && (
          <div className="space-y-6 animate-pulse-soft py-4">
            <div className="h-16 bg-surface-raised border-2 border-border shadow-hard-sm w-full"></div>
            <div className="h-32 bg-surface-raised border-2 border-border shadow-hard-sm w-full"></div>
            <div className="h-32 bg-surface-raised border-2 border-border shadow-hard-sm w-full"></div>
            <div className="text-xs font-bold text-text-tertiary mt-4 text-center">ANALYZING EVOLUTION...</div>
          </div>
        )}

        {status === 'success' && story && (
          <div className="flex flex-col gap-6">
            {isStale && (
              <div className="panel border-warning bg-surface-raised flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-warning">Analysis is outdated (new commits found)</span>
                <button
                  onClick={() => fetchStory(true)}
                  disabled={status === 'loading'}
                  className="btn btn-secondary text-xs px-2 py-1"
                >
                  Update
                </button>
              </div>
            )}
            
            {story.overall_arc && (
              <div className="panel bg-surface-hover/30 border-l-4 border-l-primary mb-4">
                <h4 className="text-[10px] font-bold text-primary uppercase mb-2 tracking-wider">Overall Arc</h4>
                <p className="text-sm text-text-primary leading-relaxed font-medium">
                  {story.overall_arc}
                </p>
              </div>
            )}

            {story.phases && story.phases.length > 0 && (
              <div className="space-y-6">
                {story.phases.map((phase, idx) => (
                  <div key={idx} className="card-flat flex flex-col gap-4">
                    <div className="flex flex-wrap items-center justify-between gap-2 border-b-2 border-border pb-3">
                      <h4 className="text-base font-bold text-text-primary">{phase.title}</h4>
                      <span className="badge badge-primary bg-surface">{phase.period}</span>
                    </div>
                    
                    {phase.narrative && (
                      <p className="text-sm text-text-primary leading-relaxed">
                        {phase.narrative}
                      </p>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Evidence Container */}
                      <div className="panel bg-surface p-4 flex flex-col gap-3">
                        <h5 className="text-[10px] font-bold text-text-secondary uppercase tracking-wider mb-1">Evidence</h5>
                        
                        {phase.key_technologies && phase.key_technologies.length > 0 && (
                          <div>
                            <span className="text-[10px] font-semibold text-text-tertiary block mb-1">Technologies</span>
                            <div className="flex flex-wrap gap-1.5">
                              {phase.key_technologies.map(t => <span key={t} className="badge badge-info">{t}</span>)}
                            </div>
                          </div>
                        )}
                        
                        {phase.key_files && phase.key_files.length > 0 && (
                          <div>
                            <span className="text-[10px] font-semibold text-text-tertiary block mb-1">Files/Modules</span>
                            <div className="flex flex-wrap gap-1.5">
                              {phase.key_files.map(f => <span key={f} className="text-xs bg-surface-hover px-1.5 py-0.5 border border-border">{f}</span>)}
                            </div>
                          </div>
                        )}

                        {phase.key_contributors && phase.key_contributors.length > 0 && (
                          <div>
                            <span className="text-[10px] font-semibold text-text-tertiary block mb-1">Contributors</span>
                            <div className="flex flex-wrap gap-1.5">
                              {phase.key_contributors.map(c => <span key={c} className="text-xs font-semibold text-text-secondary">{c}</span>)}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Significance Container */}
                      {phase.significance && (
                        <div className="panel bg-surface-raised border-primary p-4 h-full">
                          <h5 className="text-[10px] font-bold text-primary uppercase tracking-wider mb-2">Significance</h5>
                          <p className="text-sm text-text-primary leading-relaxed">
                            {phase.significance}
                          </p>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {(!story.phases || story.phases.length === 0) && !story.overall_arc && (
              <div className="text-center py-10">
                <p className="text-sm font-bold text-text-tertiary">No story phases detected.</p>
              </div>
            )}
          </div>
        )}

        {status === 'idle' && (
          <div className="flex flex-col items-center justify-center py-10 gap-4 text-center px-4 panel border-dashed">
            <div className="w-12 h-12 bg-surface-raised border-2 border-border flex items-center justify-center mb-2 shadow-hard-sm">
               <span className="font-bold text-primary text-xl">~</span>
            </div>
            <div className="text-sm font-bold text-text-primary">
              No development story generated yet.
            </div>
            <p className="text-xs text-text-secondary max-w-xs mb-2">
              Transform commit history into a chronological narrative of how this repository was built.
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
              onClick={() => fetchStory(true)}
              className="btn btn-primary"
            >
              Generate Story
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
