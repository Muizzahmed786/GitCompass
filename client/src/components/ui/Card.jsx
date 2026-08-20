import React from 'react';

export default function Card({ 
  children, 
  interactive = false, 
  className = '', 
  ...props 
}) {
  const baseClass = 'card';
  const interactiveClass = interactive ? 'card-interactive' : '';
  
  return (
    <div className={`${baseClass} ${interactiveClass} ${className}`} {...props}>
      {children}
    </div>
  );
}
