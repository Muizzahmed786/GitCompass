import React, { useEffect, useState } from 'react';

export default function CommandPalette({ isOpen, onClose }) {
  const [query, setQuery] = useState('');

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'k' && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        // Since this component might not be mounted when the shortcut is pressed,
        // the shortcut logic should actually live in Layout.jsx to open this modal.
        // For now, this just handles escape.
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[10vh]">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
      ></div>

      {/* Modal */}
      <div className="relative w-full max-w-2xl bg-[var(--color-surface-raised)] border-4 border-[var(--color-border)] shadow-[12px_12px_0px_#121212] overflow-hidden flex flex-col max-h-[80vh]">
        {/* Search Input */}
        <div className="p-4 border-b-4 border-[var(--color-border)] flex items-center gap-4 bg-[var(--color-surface)]">
          <svg className="w-6 h-6 text-[var(--color-text-secondary)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="square" strokeWidth={3} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input 
            type="text" 
            autoFocus
            className="flex-1 bg-transparent border-none outline-none text-xl font-bold font-mono placeholder-[var(--color-text-tertiary)]"
            placeholder="Search commits, files, contributors..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button onClick={onClose} className="px-2 py-1 border-2 border-[var(--color-border)] text-xs font-black uppercase shadow-[2px_2px_0px_#121212] hover:bg-[var(--color-surface-hover)] hover:translate-y-[1px] hover:translate-x-[1px] hover:shadow-[1px_1px_0px_#121212]">
            ESC
          </button>
        </div>

        {/* Results Area */}
        <div className="p-4 overflow-y-auto">
          {query ? (
            <div className="text-center py-12 text-[var(--color-text-tertiary)] font-bold uppercase tracking-widest">
              No results found for "{query}"
            </div>
          ) : (
            <div>
              <div className="text-xs font-black uppercase text-[var(--color-text-tertiary)] mb-4 tracking-widest">Recent Searches</div>
              <div className="space-y-2">
                <button className="w-full text-left p-3 border-2 border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] flex items-center justify-between">
                  <span className="font-bold">Authentication refactor</span>
                  <span className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase">Commit</span>
                </button>
                <button className="w-full text-left p-3 border-2 border-[var(--color-border)] hover:bg-[var(--color-surface-hover)] flex items-center justify-between">
                  <span className="font-bold">src/components/ui</span>
                  <span className="text-xs font-mono text-[var(--color-text-tertiary)] uppercase">Directory</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
