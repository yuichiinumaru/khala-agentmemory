import React from 'react';
import { GlassCard } from '../ui/GlassCard';
import { FpsMeter } from '../ui/FpsMeter';
import { EntropyGauge } from '../EntropyGauge';

interface StatsProps {
  stats: { nodes: number; edges: number };
}

export const Stats: React.FC<StatsProps> = ({ stats }) => {
  return (
    <div className="absolute top-6 right-6 flex gap-4 pointer-events-auto z-10 items-start">
      <GlassCard className="flex gap-6 py-2 px-6 items-center h-full">
        <div className="flex flex-col items-center">
          <span className="text-xs text-white/40 font-mono uppercase">Nodes</span>
          <span className="font-bold text-neon-green">{stats.nodes}</span>
        </div>
        <div className="w-px bg-white/10 h-8"></div>
        <div className="flex flex-col items-center">
          <span className="text-xs text-white/40 font-mono uppercase">Edges</span>
          <span className="font-bold text-neon-blue">{stats.edges}</span>
        </div>
        <div className="w-px bg-white/10 h-8"></div>
        <FpsMeter />
      </GlassCard>

      <GlassCard className="p-2">
         <EntropyGauge value={4.2} label="Sys Entropy" />
      </GlassCard>
    </div>
  );
};
