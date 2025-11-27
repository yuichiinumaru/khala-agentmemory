import React from 'react';
import { Search, Activity } from 'lucide-react';
import { GlassCard } from '../ui/GlassCard';

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
}

export const Header: React.FC<HeaderProps> = ({ searchQuery, onSearchChange }) => {
  return (
    <div className="absolute top-0 left-0 w-full p-6 z-10 flex justify-between items-start pointer-events-none">
      <div className="flex flex-col gap-4 pointer-events-auto">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-neon-blue to-neon-purple rounded-lg flex items-center justify-center shadow-[0_0_15px_rgba(0,243,255,0.3)]">
            <Activity className="text-black" size={24} />
          </div>
          <div>
            <h1 className="font-bold text-2xl tracking-tight leading-none">Supernova<span className="text-neon-blue">.js</span></h1>
            <p className="text-xs text-white/40 font-mono tracking-widest uppercase">Ultimate Edition</p>
          </div>
        </div>

        <GlassCard noPadding className="flex items-center w-80 bg-black/40">
          <Search className="ml-3 text-white/40" size={18} />
          <input
            type="text"
            placeholder="Search nodes, clusters..."
            className="bg-transparent border-none outline-none text-sm p-3 w-full text-white placeholder-white/30 font-mono"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
          />
        </GlassCard>
      </div>
    </div>
  );
};
