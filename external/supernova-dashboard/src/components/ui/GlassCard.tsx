import React, { ReactNode } from 'react';

interface GlassCardProps {
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', noPadding = false }) => {
  return (
    <div className={`glass-panel rounded-xl overflow-hidden ${noPadding ? '' : 'p-4'} ${className}`}>
      {children}
    </div>
  );
};
