import React, { useState, useEffect } from 'react';
import { api } from '../lib/api';

export default function ArchitectureTimeline({ repoId }) {
  const [shifts, setShifts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchShifts();
  }, [repoId]);

  const fetchShifts = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getAIShifts(repoId);
      setShifts(data.shifts || []);
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
        <button 
          onClick={fetchShifts}
          disabled={loading}
          className="text-sm px-3 py-1 bg-indigo-50 text-indigo-600 rounded-md hover:bg-indigo-100 transition-colors disabled:opacity-50"
        >
          {loading ? 'Analyzing...' : 'Refresh'}
        </button>
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
        <div className="text-text-secondary text-sm">No architecture shifts detected.</div>
      )}
    </div>
  );
}
