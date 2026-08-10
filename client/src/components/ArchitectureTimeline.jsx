import React, { useState } from 'react';
import { api } from '../lib/api';

export default function ArchitectureTimeline({ repoId }) {
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [generated, setGenerated] = useState(false);

  const fetchShifts = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAIShifts(repoId);
      setShifts(data.shifts || []);
      setGenerated(true);
    } catch (err) {
      setError(err.message || 'Failed to detect architecture shifts.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-surface rounded-xl shadow-sm border border-divider p-6">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-lg font-bold text-text-primary flex items-center gap-2">
          <svg className="w-5 h-5 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Architecture Shift Timeline
        </h3>
        {generated && (
          <button 
            onClick={fetchShifts}
            disabled={loading}
            className="text-sm px-3 py-1 bg-indigo-50 text-indigo-600 rounded-md hover:bg-indigo-100 transition-colors disabled:opacity-50"
          >
            {loading ? 'Analyzing...' : 'Refresh'}
          </button>
        )}
      </div>

      {loading && shifts.length === 0 ? (
        <div className="space-y-4 animate-pulse">
          <div className="h-12 bg-surface-hover rounded w-full"></div>
          <div className="h-12 bg-surface-hover rounded w-5/6"></div>
        </div>
      ) : error ? (
        <div className="bg-red-50 text-red-600 p-4 rounded-lg text-sm flex gap-3 items-start">
          <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
             <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>{error}</span>
        </div>
      ) : shifts.length > 0 ? (
        <div className="relative border-l-2 border-divider ml-3 space-y-6">
          {shifts.map((shift, index) => (
            <div key={index} className="pl-6 relative">
              <div className="absolute w-3 h-3 bg-indigo-500 rounded-full -left-[7px] top-1.5 ring-4 ring-surface"></div>
              <div className="text-xs font-semibold text-indigo-600 mb-1">{shift.date}</div>
              <div className="font-bold text-text-primary mb-1">{shift.title}</div>
              <div className="text-sm text-text-secondary">{shift.description}</div>
            </div>
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-8 gap-3">
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
          <p className="text-xs text-text-tertiary">Click to analyze commit history for major changes</p>
        </div>
      )}
    </div>
  );
}
