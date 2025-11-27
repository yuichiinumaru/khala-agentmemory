import React, { forwardRef } from 'react';

// GraphCanvas is now a pure presentational component.
// It receives the ref from App.tsx where the hook is now centralized.
export const GraphCanvas = forwardRef<HTMLDivElement>((props, ref) => {
  return (
    <div className="absolute inset-0 z-0">
        <div className="w-full h-full bg-obsidian relative overflow-hidden group">
        <div
            ref={ref}
            className="w-full h-full cursor-grab active:cursor-grabbing transition-opacity duration-1000 ease-in opacity-0 animate-in fade-in fill-mode-forwards"
            style={{ animationDelay: '0.2s', animationDuration: '1.5s' }}
            onContextMenu={(e) => e.preventDefault()}
        />
        <div className="absolute inset-0 pointer-events-none opacity-[0.03]"
            style={{
                backgroundImage: 'linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px)',
                backgroundSize: '100px 100px'
            }}>
        </div>
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_0%,rgba(5,5,5,0.8)_100%)]" />
        </div>
    </div>
  );
});

GraphCanvas.displayName = 'GraphCanvas';
