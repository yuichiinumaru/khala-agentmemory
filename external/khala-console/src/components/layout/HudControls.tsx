import React, { useState } from 'react';
import { GlassCard } from '../ui/GlassCard';
import { LayoutType } from '../../types';
import { GraphVizAPI } from '../../hooks/useGraphApplication';
import {
  Activity,
  Database,
  Layout,
  Layers,
  Settings,
  Download,
  Share2
} from 'lucide-react';

interface HudControlsProps {
  currentLayout: LayoutType;
  onLayoutChange: (layout: LayoutType) => void;
  graphApi: GraphVizAPI | null;
}

const layoutOptions = [
  { id: LayoutType.FORCE_ATLAS, icon: Activity, label: 'Force' },
  { id: LayoutType.CIRCLE, icon: Database, label: 'Circle' },
  { id: LayoutType.GRID, icon: Layout, label: 'Grid' },
  { id: LayoutType.RANDOM, icon: Layers, label: 'Chaos' },
];

export const HudControls: React.FC<HudControlsProps> = ({ currentLayout, onLayoutChange, graphApi }) => {
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <div
      className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10 pointer-events-auto"
      onClick={(e) => e.stopPropagation()} // Prevent clicks from closing menus on the parent
    >
      <GlassCard className="flex items-center gap-2 p-2 rounded-2xl relative">

        {isSettingsOpen && (
           <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 animate-in slide-in-from-bottom-2 fade-in">
             <GlassCard className="w-48 p-2 flex flex-col gap-2">
               <span className="text-xs font-mono text-white/50 px-2 uppercase">Data Controls</span>
               <button
                 onClick={() => graphApi?.exportData()}
                 className="flex items-center gap-2 p-2 hover:bg-white/10 rounded text-xs text-neon-blue transition-colors"
               >
                 <Download size={14} /> Export JSON
               </button>
               <button className="flex items-center gap-2 p-2 hover:bg-white/10 rounded text-xs text-white/70 transition-colors">
                 <Share2 size={14} /> Share View
               </button>
             </GlassCard>
           </div>
        )}

        {layoutOptions.map((l) => (
          <button
            key={l.id}
            onClick={() => onLayoutChange(l.id)}
            className={`flex flex-col items-center justify-center w-16 h-16 rounded-xl transition-all duration-300 ${
              currentLayout === l.id
                ? 'bg-neon-blue/20 text-neon-blue shadow-[0_0_15px_rgba(0,243,255,0.2)] border border-neon-blue/30'
                : 'text-white/40 hover:bg-white/5 hover:text-white'
            }`}
          >
            <l.icon size={20} />
            <span className="text-[10px] mt-1 font-medium">{l.label}</span>
          </button>
        ))}
        <div className="w-px h-10 bg-white/10 mx-2"></div>
        <button
          onClick={() => setIsSettingsOpen(!isSettingsOpen)}
          className={`flex flex-col items-center justify-center w-16 h-16 rounded-xl transition-all ${
            isSettingsOpen ? 'bg-white/10 text-white' : 'text-white/40 hover:bg-white/5 hover:text-white'
          }`}
        >
          <Settings size={20} />
          <span className="text-[10px] mt-1 font-medium">Config</span>
        </button>
      </GlassCard>
    </div>
  );
};
