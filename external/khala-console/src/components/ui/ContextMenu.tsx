import React from 'react';
import { GlassCard } from './GlassCard';
import { Crosshair, Eye, Bot, X } from 'lucide-react';

interface ContextMenuProps {
  x: number;
  y: number;
  nodeId: string;
  onClose: () => void;
  onAction: (action: 'focus' | 'filter' | 'analyze') => void;
}

export const ContextMenu: React.FC<ContextMenuProps> = ({ x, y, nodeId, onClose, onAction }) => {
  return (
    <div 
      className="fixed z-50 animate-in fade-in zoom-in-95 duration-200"
      style={{ top: y, left: x }}
    >
      <GlassCard className="w-48 border-neon-blue/30 shadow-[0_0_30px_rgba(0,243,255,0.2)]" noPadding>
        <div className="p-3 border-b border-white/10 flex justify-between items-center bg-white/5">
          <span className="font-mono text-xs text-neon-blue font-bold truncate max-w-[120px]">{nodeId}</span>
          <button onClick={onClose} className="text-white/40 hover:text-white">
            <X size={14} />
          </button>
        </div>
        <div className="p-1">
          <button 
            onClick={() => onAction('focus')}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-white hover:bg-neon-blue/20 hover:text-neon-blue rounded transition-colors text-left"
          >
            <Crosshair size={14} />
            <span>Focus Node</span>
          </button>
          <button 
            onClick={() => onAction('filter')}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-white hover:bg-neon-purple/20 hover:text-neon-purple rounded transition-colors text-left"
          >
            <Eye size={14} />
            <span>Isolate Cluster</span>
          </button>
          <button 
            onClick={() => onAction('analyze')}
            className="w-full flex items-center gap-2 px-3 py-2 text-xs text-white hover:bg-neon-green/20 hover:text-neon-green rounded transition-colors text-left"
          >
            <Bot size={14} />
            <span>Ask Oracle</span>
          </button>
        </div>
      </GlassCard>
    </div>
  );
};