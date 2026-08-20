import React from 'react';

export default function Badge({ 
  children, 
  variant = 'default', 
  className = '' 
}) {
  const baseClass = 'badge';
  const variantClass = variant !== 'default' ? `badge-${variant}` : '';
  
  return (
    <span className={`${baseClass} ${variantClass} ${className}`}>
      {children}
    </span>
  );
}
