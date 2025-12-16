import React from 'react';
import { GlassCard } from '../ui/GlassCard';
import { FpsMeter } from '../ui/FpsMeter';
interface StatsProps {
  stats: { nodes: number; edges: number };
}

export const Stats: React.FC<StatsProps> = ({ stats }) => {
  return (
    <div className="absolute top-6 right-6 flex gap-4 pointer-events-auto z-10">
      <GlassCard className="flex gap-6 py-2 px-6">
        <div className="flex flex-col items-center">
          <span className="text-xs text-white/40 font-mono uppercase">Nodes</span>
          <span className="font-bold text-neon-green">{stats.nodes}</span>
        </div>
        <div className="w-px bg-white/10"></div>
        <div className="flex flex-col items-center">
          <span className="text-xs text-white/40 font-mono uppercase">Edges</span>
          <span className="font-bold text-neon-blue">{stats.edges}</span>
        </div>
        <div className="w-px bg-white/10"></div>
        <FpsMeter />
      </GlassCard>
    </div>
  );
};
