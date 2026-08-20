import React from 'react';

export default function Input({ className = '', ...props }) {
  return (
    <input 
      className={`w-full p-3 border-2 border-[var(--color-border)] bg-[var(--color-surface-raised)] font-mono text-sm focus:outline-none focus:ring-0 focus:shadow-[4px_4px_0px_#121212] transition-shadow ${className}`} 
      {...props} 
    />
  );
}
