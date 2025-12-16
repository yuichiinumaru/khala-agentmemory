import React, { ReactNode } from 'react';

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  children: ReactNode;
  className?: string;
  noPadding?: boolean;
}

export const GlassCard: React.FC<GlassCardProps> = ({ children, className = '', noPadding = false, ...props }) => {
  return (
    <div {...props} className={`glass-panel rounded-xl overflow-hidden ${noPadding ? '' : 'p-4'} ${className}`}>
      {children}
    </div>
  );
};
